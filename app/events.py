from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import LiveSession, LiveParticipant, Option

@socketio.on('host_join')
def handle_host_join(data):
    pin = data.get('pin')
    join_room(f"host_{pin}")
    join_room(pin)

@socketio.on('player_join')
def handle_player_join(data):
    pin = data.get('pin')
    name = data.get('name')
    
    session = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if session:
        participant = LiveParticipant(session_id=session.id, name=name)
        db.session.add(participant)
        db.session.commit()
        
        join_room(pin)
        # Notify host that player joined
        emit('player_joined', {'name': name, 'id': participant.id}, to=f"host_{pin}")
        # Send confirmation to player
        emit('join_success', {'message': 'Joined successfully!', 'participant_id': participant.id})
    else:
        emit('join_error', {'message': 'Invalid PIN or session inactive'})

@socketio.on('next_question')
def handle_next_question(data):
    pin = data.get('pin')
    session = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if session:
        session.current_question_index += 1
        db.session.commit()
        
        quiz = session.quiz
        if session.current_question_index <= len(quiz.questions):
            question = quiz.questions[session.current_question_index - 1]
            options = [{'id': o.id, 'text': o.text} for o in question.options]
            
            question_data = {
                'index': session.current_question_index,
                'total': len(quiz.questions),
                'text': question.text,
                'type': question.question_type,
                'media_url': question.media_url,
                'options': options
            }
            emit('new_question', question_data, to=pin)
        else:
            emit('quiz_end', {}, to=pin)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    pin = data.get('pin')
    participant_id = data.get('participant_id')
    answer = data.get('answer')
    
    session = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if session:
        participant = LiveParticipant.query.get(participant_id)
        if not participant:
            return

        question = session.quiz.questions[session.current_question_index - 1]
        
        is_correct = False
        if question.question_type == 'text':
            # Text uses strict match, could be manual
            text_ans_correct = next((o for o in question.options if o.is_correct and o.text.lower() == str(answer).lower()), None)
            if text_ans_correct:
                is_correct = True
        elif question.question_type == 'multiple':
            # Multiple is complex for real-time without arrays, we will handle list of options
            correct_options = [str(o.id) for o in question.options if o.is_correct]
            if isinstance(answer, list) and set(str(a) for a in answer) == set(correct_options) and len(correct_options) > 0:
                is_correct = True
        else:
            option = Option.query.get(answer)
            if option and option.is_correct:
                is_correct = True
                
        if is_correct:
            participant.score += 100
            db.session.commit()
            
        emit('answer_received', {'participant_id': participant.id, 'name': participant.name}, to=f"host_{pin}")

@socketio.on('show_leaderboard')
def handle_show_leaderboard(data):
    pin = data.get('pin')
    session = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if session:
        from sqlalchemy import desc
        participants = LiveParticipant.query.filter_by(session_id=session.id).order_by(desc(LiveParticipant.score)).limit(5).all()
        leaders = [{'name': p.name, 'score': p.score} for p in participants]
        emit('leaderboard_data', {'leaders': leaders}, to=pin)
        
@socketio.on('end_session')
def handle_end_session(data):
    pin = data.get('pin')
    session = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if session:
        session.is_active = False
        db.session.commit()
        emit('session_ended', {}, to=pin)
