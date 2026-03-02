import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db, Quiz, Question, Option, Submission
import warnings

warnings.filterwarnings("ignore")

class QCMTestCaseV2(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def create_quiz(self):
        data = [
            ('title', 'V2 Quiz'),
            ('description', 'Test'),
            ('duration', '10'),
            ('time_per_question', '15'), # New field
            ('questions[1][text]', 'Q1'),
            ('questions[1][correct]', '0'),
            ('questions[1][options][]', 'A'),
            ('questions[1][options][]', 'B')
        ]
        return self.app.post('/teacher/add_quiz', data=data, follow_redirects=True)

    def test_create_with_timer(self):
        response = self.create_quiz()
        if response.status_code != 302 and response.status_code != 200:
             print(f"Failed to create quiz. Status: {response.status_code}")
             print(response.data.decode('utf-8'))
        
        with app.app_context():
            quiz = Quiz.query.first()
            if quiz is None:
                print("Quiz is None! Response data:")
                print(response.data.decode('utf-8'))
            self.assertIsNotNone(quiz)
            self.assertEqual(quiz.time_per_question, 15)
            print("Create Quiz with Timer: OK")

    def test_edit_quiz(self):
        self.create_quiz()
        with app.app_context():
            quiz_id = Quiz.query.first().id

        # Edit data: Change title and time per question
        data = [
            ('title', 'V2 Quiz Edited'),
            ('description', 'Test Edited'),
            ('duration', '20'),
            ('time_per_question', '45'),
            ('questions[1][text]', 'Q1 Edited'), # Same question
            ('questions[1][correct]', '1'),
            ('questions[1][options][]', 'A'),
            ('questions[1][options][]', 'B')
        ]
        
        response = self.app.post(f'/teacher/quiz/edit/{quiz_id}', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with app.app_context():
            quiz = Quiz.query.get(quiz_id)
            self.assertEqual(quiz.title, 'V2 Quiz Edited')
            self.assertEqual(quiz.time_per_question, 45)
            self.assertEqual(quiz.questions[0].text, 'Q1 Edited')
            print("Edit Quiz: OK")

    def test_delete_quiz(self):
        self.create_quiz()
        with app.app_context():
            quiz_id = Quiz.query.first().id
        
        response = self.app.post(f'/teacher/quiz/delete/{quiz_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with app.app_context():
            quiz = Quiz.query.get(quiz_id)
            self.assertIsNone(quiz)
            print("Delete Quiz: OK")

if __name__ == '__main__':
    unittest.main()
