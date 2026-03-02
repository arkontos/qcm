from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Message, User
from sqlalchemy import or_

bp = Blueprint('messages', __name__)

@bp.route('/')
@login_required
def inbox():
    # Only show root messages (threads) involving the current user
    # A thread involves the user if they are the sender, receiver, or involved in any replies
    
    # helper to see if a message is deleted for current user
    def is_deleted(msg):
        if msg.sender_id == current_user.id and msg.deleted_by_sender: return True
        if msg.receiver_id == current_user.id and msg.deleted_by_receiver: return True
        return False
        
    # Get all threads
    # For a thread to be visible, it must contain at least 1 message not deleted by the user
    threads = Message.query.filter(
        Message.parent_id.is_(None)
    ).order_by(Message.timestamp.desc()).all()
    
    thread_data = []
    for thread in threads:
        all_msgs = [thread] + thread.replies
        
        # Filter messages relevant to current_user
        user_msgs = [m for m in all_msgs if m.sender_id == current_user.id or m.receiver_id == current_user.id]
        if not user_msgs: continue # Not part of this thread
        
        # Filter out deleted messages
        visible_msgs = [m for m in user_msgs if not is_deleted(m)]
        if not visible_msgs: continue # Entire thread deleted for user
        
        # Check if ANY visible message in this thread is unread AND addressed to the user
        has_unread = any(not m.is_read and m.receiver_id == current_user.id for m in visible_msgs)
        
        # Sort all VISIBLE messages to get the latest interaction time
        sorted_msgs = sorted(visible_msgs, key=lambda m: m.timestamp, reverse=True)
        latest_msg = sorted_msgs[0]
        
        # Determine the "other person" in the root of the thread for display purposes
        other_user = thread.receiver if thread.sender_id == current_user.id else thread.sender
        
        thread_data.append({
            'id': thread.id,
            'subject': thread.subject or "No Subject",
            'other_user': other_user,
            'latest_timestamp': latest_msg.timestamp,
            'has_unread': has_unread
        })
        
    # Sort threads by the latest activity
    thread_data.sort(key=lambda x: x['latest_timestamp'], reverse=True)

    # Resolve contacts for "New Message" modal
    if current_user.role == 'student':
        contacts = []
        for cls in current_user.classrooms:
            if cls.teacher not in contacts:
                contacts.append(cls.teacher)
    elif current_user.role == 'teacher':
        contacts = []
        for cls in current_user.taught_classes:
            for student in cls.students:
                if student not in contacts:
                    contacts.append(student)
    else:
        contacts = User.query.filter(User.id != current_user.id).all()

    return render_template('messages.html', threads=thread_data, contacts=contacts, active_thread=None)

@bp.route('/<int:thread_id>')
@login_required
def view_thread(thread_id):
    thread = Message.query.get_or_404(thread_id)
    
    # Ensure this is a root message
    if thread.parent_id is not None:
        return redirect(url_for('messages.view_thread', thread_id=thread.parent_id))
        
    def is_deleted(msg):
        if msg.sender_id == current_user.id and msg.deleted_by_sender: return True
        if msg.receiver_id == current_user.id and msg.deleted_by_receiver: return True
        return False
        
    all_msgs = [thread] + thread.replies
    user_msgs = [m for m in all_msgs if m.sender_id == current_user.id or m.receiver_id == current_user.id]
    visible_msgs = [m for m in user_msgs if not is_deleted(m)]
    
    if not visible_msgs:
        flash("You don't have permission to view this thread or it was deleted.", "error")
        return redirect(url_for('messages.inbox'))
        
    # Mark all unread visible messages addressed to the user as read
    for msg in visible_msgs:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    sorted_msgs = sorted(visible_msgs, key=lambda m: m.timestamp)
    
    # Contacts list for New Message Modal
    contacts = User.query.filter(User.id != current_user.id).all() if current_user.role not in ['student', 'teacher'] else []
    if current_user.role == 'student':
        for cls in current_user.classrooms:
            if cls.teacher not in contacts: contacts.append(cls.teacher)
    elif current_user.role == 'teacher':
        for cls in current_user.taught_classes:
            for student in cls.students:
                if student not in contacts: contacts.append(student)
                
    # Determine default reply-to person (whoever didn't send the last visible message, or root owner)
    reply_to = thread.sender if thread.sender_id != current_user.id else thread.receiver
    
    # We still need thread_data to render the sidebar. We rebuild it using the same logic as inbox()
    all_threads = Message.query.filter(Message.parent_id.is_(None)).all()
    thread_data = []
    for t in all_threads:
        t_all = [t] + t.replies
        t_user = [m for m in t_all if m.sender_id == current_user.id or m.receiver_id == current_user.id]
        t_vis = [m for m in t_user if not is_deleted(m)]
        if not t_vis: continue
        
        has_unread = any(not m.is_read and m.receiver_id == current_user.id for m in t_vis)
        t_latest = sorted(t_vis, key=lambda m: m.timestamp, reverse=True)[0]
        other_user = t.receiver if t.sender_id == current_user.id else t.sender
        thread_data.append({
            'id': t.id,
            'subject': t.subject or "No Subject",
            'other_user': other_user,
            'latest_timestamp': t_latest.timestamp,
            'has_unread': has_unread
        })
    thread_data.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return render_template('messages.html', 
                            threads=thread_data, 
                            contacts=contacts, 
                            active_thread=thread,
                            thread_messages=sorted_msgs,
                            reply_to=reply_to)

@bp.route('/send', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form.get('receiver_id')
    subject = request.form.get('subject')
    content = request.form.get('content')
    parent_id = request.form.get('parent_id')
    
    if receiver_id and content:
        new_msg = Message(
            sender_id=current_user.id,
            receiver_id=int(receiver_id),
            subject=subject if not parent_id else None,
            content=content,
            parent_id=int(parent_id) if parent_id else None
        )
        db.session.add(new_msg)
        db.session.commit()
        flash('Message sent successfully!', 'success')
        
        if parent_id:
            return redirect(url_for('messages.view_thread', thread_id=parent_id))
    else:
        flash('Failed to send message. Please ensure a recipient and message body are provided.', 'error')
        
    return redirect(url_for('messages.inbox'))

@bp.route('/<int:thread_id>/delete', methods=['POST'])
@login_required
def delete_thread(thread_id):
    thread = Message.query.get_or_404(thread_id)
    if thread.parent_id is not None:
        thread = Message.query.get_or_404(thread.parent_id)
        
    all_msgs = [thread] + thread.replies
    
    deleted_count = 0
    for msg in all_msgs:
        if msg.sender_id == current_user.id:
            msg.deleted_by_sender = True
            deleted_count += 1
        if msg.receiver_id == current_user.id:
            msg.deleted_by_receiver = True
            deleted_count += 1
            
    if deleted_count > 0:
        db.session.commit()
        flash('Conversation deleted.', 'info')
    else:
        flash('Could not delete conversation.', 'error')
        
    return redirect(url_for('messages.inbox'))
