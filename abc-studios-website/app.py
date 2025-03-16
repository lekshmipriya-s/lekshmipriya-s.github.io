from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

# Get base directory path
base_dir = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask app with correct paths
app = Flask(__name__, 
            template_folder=os.path.join('abc-studios-website', 'src', 'pages'),
            static_folder=os.path.join('abc-studios-website', 'src'))

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Lekshm!2004@localhost/abc'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'abc-studios-website', 'src', 'assets', 'uploads', 'resumes')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)  # Changed from sent_at

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'subject': self.subject,
            'message': self.message,
            'submitted_at': self.submitted_at.isoformat()  # Changed from sent_at
        }
# Job Application Model
class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    resume_file = db.Column(db.String(200), nullable=False)
    cover_letter = db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'resume_file': self.resume_file,
            'cover_letter': self.cover_letter,
            'applied_at': self.applied_at.isoformat(),
            'status': self.status
        }

# Routes
@app.route('/')
@app.route('/home')
def home():
    return render_template('index.html')  # Changed from home.html to index.html

@app.route('/about')
def about():
    return render_template('about_us.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/tournaments')
def tournaments():
    return render_template('tournaments.html')

@app.route('/tournament-register')
def tournament_register():
    return render_template('tournament-register.html')


@app.route('/join')
def join():
    return render_template('join.html')



@app.route('/api/apply', methods=['POST'])
def submit_application():
    try:
        # Get form data
        full_name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        cover_letter = request.form.get('coverLetter')

        # Validate required fields
        if not all([full_name, email, phone]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Handle resume file
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed types: PDF, DOC, DOCX'}), 400

        try:
            # Create secure filename with timestamp
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Create new application
            application = JobApplication(
                full_name=full_name,
                email=email,
                phone=phone,
                resume_file=filename,
                cover_letter=cover_letter
            )

            db.session.add(application)
            db.session.commit()

            return jsonify({
                'message': 'Application submitted successfully',
                'application_id': application.id,
                'data': application.to_dict()
            }), 201

        except Exception as e:
            # Clean up file if database operation fails
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to submit application',
            'details': str(e)
        }), 500
@app.route('/admin')
def admin():
    applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).all()
    return render_template('admin.html', applications=applications)
@app.route('/api/applications')
def get_applications():
    try:
        applications = JobApplication.query.order_by(JobApplication.applied_at.desc()).all()
        return jsonify([app.to_dict() for app in applications])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/application/<int:app_id>')
def get_application(app_id):
    try:
        application = JobApplication.query.get_or_404(app_id)
        return jsonify(application.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    # Add this route before if __name__ == '__main__':
@app.route('/api/application/<int:app_id>/status', methods=['PUT'])
def update_application_status(app_id):
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400

        status = data['status']
        if status not in ['pending', 'accepted', 'rejected']:
            return jsonify({'error': 'Invalid status value'}), 400

        application = JobApplication.query.get_or_404(app_id)
        application.status = status
        db.session.commit()

        return jsonify({
            'message': 'Status updated successfully',
            'application': application.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/assets/uploads/resumes/<path:filename>')
def download_resume(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/contact_test')
def contact_test():
    return render_template('contact_test.html')
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Debug print
        print(f"Received contact form: {name}, {email}, {phone}, {subject}")

        # Validate required fields
        if not all([name, email, phone, subject, message]):
            return jsonify({'error': 'All fields are required'}), 400

        # Create new contact message
        contact = Contact(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )

        db.session.add(contact)
        db.session.commit()

        print(f"Contact saved with ID: {contact.id}")

        return jsonify({
            'message': 'Message sent successfully',
            'contact_id': contact.id,
            'data': contact.to_dict()
        }), 201

    except Exception as e:
        print(f"Error saving contact: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':

    # Debug prints to verify paths
    print(f"Base Directory: {base_dir}")
    print(f"Template Folder: {os.path.join('abc-studios-website', 'src', 'pages')}")
    print(f"Static Folder: {os.path.join('abc-studios-website', 'src')}")
    print(f"Upload Folder: {app.config['UPLOAD_FOLDER']}")
    

    with app.app_context():
        db.create_all()
    app.run(debug=True)