import unittest
from app import app, db, Quiz, Question, Option, Submission
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

class QCMTestCase(unittest.TestCase):
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

    def test_full_flow(self):
        # 1. Teacher creates a quiz
        print("\nTesting: Teacher creates a quiz...")
        quiz_data = {
            'title': 'Unit Test Quiz',
            'description': 'Testing flow',
            'duration': 5,
            # Questions simulation based on the form structure we analyzed
            'questions[1][text]': 'What is 2+2?',
            'questions[1][correct]': 1, # Option index 1 (0-based) -> 4
            'questions[1][options][]': ['3', '4', '5', '6'] # Passed as separate values usually, strictly list form in Flask test client can be tricky
        }
        
        # Flask test client handling of lists in form data needs proper formatting
        # We need to pass multiple values for the same key 'questions[1][options][]'
        # But requests dict doesn't support duplicates easily unless list.
        # However, werkzeug/flask test client supports passing a MultiDict or list of tuples.
        
        data = {
            'title': 'Unit Test Quiz',
            'description': 'Testing flow',
            'duration': 5,
            'questions[1][text]': 'What is 2+2?',
            'questions[1][correct]': 1,
        }
        # MultiDict simulation for list
        data_list = list(data.items())
        data_list.append(('questions[1][options][]', '3'))
        data_list.append(('questions[1][options][]', '4'))
        data_list.append(('questions[1][options][]', '5'))
        data_list.append(('questions[1][options][]', '6'))

        response = self.app.post('/teacher/add_quiz', data=data_list, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unit Test Quiz', response.data)
        
        with app.app_context():
            quiz = Quiz.query.first()
            self.assertIsNotNone(quiz)
            self.assertEqual(len(quiz.questions), 1)
            self.assertEqual(quiz.questions[0].text, 'What is 2+2?')
            quiz_id = quiz.id
            q1_id = quiz.questions[0].id
            correct_opt = [opt for opt in quiz.questions[0].options if opt.is_correct][0]

        # 2. Student Joins
        print("Testing: Student joins quiz...")
        response = self.app.post(f'/student/join/{quiz_id}', data={'name': 'Test Student'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'What is 2+2?', response.data)
        
        # 3. Student Submits
        print("Testing: Student submits answers...")
        # Select the correct option
        submit_data = {
            f'q_{q1_id}': correct_opt.id
        }
        response = self.app.post(f'/student/submit/{quiz_id}', data=submit_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Congratulations', response.data)
        self.assertIn(b'1 out of 1', response.data)

        # 4. Teacher views results
        print("Testing: Teacher views results...")
        response = self.app.get(f'/teacher/quiz/{quiz_id}/results')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Student', response.data)
        self.assertIn(b'Passed', response.data)

if __name__ == '__main__':
    unittest.main()
