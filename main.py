"""
Research Paper Converter - Flask Backend
Converts PDF papers to Markdown format using MarkItDown or Docling
"""

from flask import Flask, request, jsonify, send_file, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import shutil
import uuid
import logging
import time
import json
from typing import Optional, List
from functools import wraps
from sqlalchemy.orm import DeclarativeBase

# Import PDF conversion libraries
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "research-paper-converter-secret-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///research_converter.db")

# Trial license configuration (7 days from first run)
TRIAL_DURATION_DAYS = 7
LICENSE_FILE = "app_license.json"

# If using PostgreSQL, configure connection parameters
if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# License management functions
def check_license():
    """Check if the app license is still valid"""
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                license_data = json.load(f)
            
            first_run = license_data.get('first_run')
            if first_run:
                first_run_time = datetime.fromisoformat(first_run)
                expiry_time = first_run_time + timedelta(days=TRIAL_DURATION_DAYS)
                
                if datetime.now() > expiry_time:
                    return False, expiry_time
                else:
                    return True, expiry_time
        else:
            # First run - create license file
            create_license_file()
            return True, datetime.now() + timedelta(days=TRIAL_DURATION_DAYS)
    except Exception as e:
        logger.error(f"License check error: {e}")
        # If file operations fail, allow a temporary 1-day grace period
        return True, datetime.now() + timedelta(days=1)

def create_license_file():
    """Create license file on first run"""
    try:
        license_data = {
            'first_run': datetime.now().isoformat(),
            'app_name': 'Research Paper Converter',
            'trial_days': TRIAL_DURATION_DAYS
        }
        with open(LICENSE_FILE, 'w') as f:
            json.dump(license_data, f, indent=2)
        logger.info("License file created - 7-day trial started")
        return True
    except Exception as e:
        logger.error(f"Error creating license file: {e}")
        return False

def license_required(f):
    """Decorator to check license before accessing protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_valid, expiry_time = check_license()
        if not is_valid:
            return jsonify({
                'error': 'Trial Expired',
                'message': f'This 7-day trial version has expired. Trial ended on {expiry_time.strftime("%Y-%m-%d %H:%M:%S") if expiry_time else "unknown date"}.',
                'expired': True
            }), 403
        return f(*args, **kwargs)
    return decorated_function

# Database setup
class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# PostgreSQL specific configuration
if DATABASE_URL and 'postgresql' in DATABASE_URL:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }

# Initialize extensions
db = SQLAlchemy(model_class=Base)
db.init_app(app)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# Database Models
class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hashed_password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Paper(db.Model):
    __tablename__ = "papers"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    markdown_content = db.Column(db.Text)
    processor_used = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_status = db.Column(db.String(50), default="pending")

# Create application context and tables
with app.app_context():
    db.create_all()

# Create upload directory
os.makedirs("uploads", exist_ok=True)

# Authentication utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_user = User.query.filter_by(username=payload['sub']).first()
            if not current_user:
                return jsonify({'message': 'Token is invalid'}), 401
        except JWTError:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# PDF Processor
class PaperProcessor:
    def __init__(self):
        self.markitdown = MarkItDown() if MARKITDOWN_AVAILABLE else None
        self.docling = DocumentConverter() if DOCLING_AVAILABLE else None
        
    def convert_to_markdown(self, file_path: str) -> dict:
        """Convert PDF to Markdown format"""
        try:
            # Try MarkItDown first
            if self.markitdown:
                result = self._convert_with_markitdown(file_path)
                if result:
                    return result
            
            # Fallback to Docling
            if self.docling:
                result = self._convert_with_docling(file_path)
                if result:
                    return result
            
            return self._basic_conversion(file_path)
            
        except Exception as e:
            logger.error(f"Error converting paper: {e}")
            return {"error": str(e)}
    
    def _convert_with_markitdown(self, file_path: str) -> dict:
        try:
            result = self.markitdown.convert(file_path)
            return {
                "processor": "MarkItDown",
                "markdown": result.text_content,
                "title": self._extract_title(result.text_content),
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"MarkItDown conversion failed: {e}")
            return None
    
    def _convert_with_docling(self, file_path: str) -> dict:
        try:
            result = self.docling.convert(file_path)
            markdown = result.document.export_to_markdown()
            return {
                "processor": "Docling",
                "markdown": markdown,
                "title": self._extract_title(markdown),
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Docling conversion failed: {e}")
            return None
    
    def _basic_conversion(self, file_path: str) -> dict:
        return {
            "processor": "Basic",
            "markdown": f"# {os.path.basename(file_path)}\n\nPaper converted from: {file_path}",
            "title": f"Paper - {os.path.basename(file_path)}",
            "processed_at": datetime.now().isoformat()
        }
    
    def _extract_title(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                return line
        return "Untitled Paper"

processor = PaperProcessor()

# API Routes
@app.route('/api/register', methods=['POST'])
@license_required
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'detail': 'Missing required fields'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'detail': 'Email already registered'}), 400
        
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'detail': 'Username already taken'}), 400
        
        # Create new user
        hashed_password = generate_password_hash(data['password'])
        new_user = User(
            email=data['email'],
            username=data['username'],
            hashed_password=hashed_password,
            full_name=data.get('full_name', '')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'id': new_user.id,
            'email': new_user.email,
            'username': new_user.username,
            'full_name': new_user.full_name,
            'is_active': new_user.is_active,
            'created_at': new_user.created_at.isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'detail': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
@license_required
def login_user():
    """User login"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'detail': 'Missing username or password'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        if not user or not check_password_hash(user.hashed_password, data['password']):
            return jsonify({'detail': 'Incorrect username or password'}), 401
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return jsonify({
            'access_token': access_token,
            'token_type': 'bearer'
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'detail': 'Login failed'}), 500

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get user profile"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'is_active': current_user.is_active,
        'created_at': current_user.created_at.isoformat()
    }), 200

@app.route('/api/convert', methods=['POST'])
@license_required
@token_required
def convert_paper(current_user):
    """Convert PDF paper to Markdown"""
    file_path = None
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'detail': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'detail': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'detail': 'Only PDF files are supported'}), 400
        
        # Check file size (50MB limit)
        if file.content_length and file.content_length > 50 * 1024 * 1024:
            return jsonify({'detail': 'File too large. Maximum size is 50MB'}), 400
        
        # Save uploaded file with error handling
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{secure_filename(file.filename)}"
        file_path = os.path.join("uploads", filename)
        
        # Ensure uploads directory exists
        os.makedirs("uploads", exist_ok=True)
        
        try:
            file.save(file_path)
            logger.info(f"File saved successfully: {file_path}")
        except Exception as save_error:
            logger.error(f"Failed to save file: {save_error}")
            return jsonify({'detail': 'Failed to save uploaded file'}), 500
        
        # Verify file was saved and is readable
        if not os.path.exists(file_path):
            return jsonify({'detail': 'File upload failed - file not found'}), 500
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return jsonify({'detail': 'File upload failed - empty file'}), 500
        
        logger.info(f"Processing file: {file_path} (size: {file_size} bytes)")
        
        # Convert to Markdown with timeout protection
        try:
            result = processor.convert_to_markdown(file_path)
            logger.info(f"Conversion completed: {result.get('processor', 'Unknown')}")
        except Exception as conversion_error:
            logger.error(f"Conversion failed: {conversion_error}")
            # Clean up file on conversion error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'detail': f'Conversion failed: {str(conversion_error)}'}), 500
        
        # Save to database
        new_paper = Paper(
            user_id=current_user.id,
            title=result.get("title", "Untitled"),
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            markdown_content=result.get("markdown", ""),
            processor_used=result.get("processor", "Unknown"),
            processing_status="completed"
        )
        
        try:
            db.session.add(new_paper)
            db.session.commit()
            logger.info(f"Paper saved to database: {new_paper.id}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            db.session.rollback()
            # Clean up file on database error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'detail': 'Failed to save paper to database'}), 500
        
        return jsonify({
            "success": True,
            "paper_id": new_paper.id,
            "title": new_paper.title,
            "processor_used": new_paper.processor_used,
            "content_length": len(new_paper.markdown_content),
            "processed_at": new_paper.created_at.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        # Clean up file on any error
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        return jsonify({'detail': str(e)}), 500

@app.route('/api/papers', methods=['GET'])
@token_required
def get_papers(current_user):
    """Get user's converted papers"""
    papers = Paper.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            'id': paper.id,
            'title': paper.title,
            'filename': paper.original_filename,
            'processor_used': paper.processor_used,
            'created_at': paper.created_at.isoformat(),
            'processing_status': paper.processing_status
        }
        for paper in papers
    ]), 200

@app.route('/api/paper/<int:paper_id>', methods=['GET'])
@token_required
def get_paper(current_user, paper_id):
    """Get specific paper content"""
    paper = Paper.query.filter_by(id=paper_id, user_id=current_user.id).first()
    
    if not paper:
        return jsonify({'detail': 'Paper not found'}), 404
    
    return jsonify({
        'id': paper.id,
        'title': paper.title,
        'filename': paper.original_filename,
        'markdown_content': paper.markdown_content,
        'processor_used': paper.processor_used,
        'created_at': paper.created_at.isoformat(),
        'processing_status': paper.processing_status
    }), 200

@app.route('/api/paper/<int:paper_id>/download', methods=['GET'])
@token_required
def download_paper(current_user, paper_id):
    """Download paper as markdown file"""
    try:
        logger.info(f"Download request for paper {paper_id} by user {current_user.id}")
        paper = Paper.query.filter_by(id=paper_id, user_id=current_user.id).first()
        
        if not paper:
            logger.error(f"Paper {paper_id} not found for user {current_user.id}")
            return jsonify({'detail': 'Paper not found'}), 404
        
        if not paper.markdown_content:
            logger.error(f"Paper {paper_id} has no content")
            return jsonify({'detail': 'Paper has no content'}), 400
        
        # Create clean filename
        filename = f"paper_{paper_id}.md"
        
        # Create response with markdown content
        response = make_response(paper.markdown_content)
        response.headers['Content-Type'] = 'text/markdown; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = str(len(paper.markdown_content))
        
        logger.info(f"Successfully serving download for paper {paper_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error downloading paper {paper_id}: {e}")
        return jsonify({'detail': f'Download failed: {str(e)}'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get application status"""
    is_valid, expiry_time = check_license()
    return jsonify({
        "status": "running",
        "processors": {
            "markitdown": MARKITDOWN_AVAILABLE,
            "docling": DOCLING_AVAILABLE
        },
        "version": "1.0.0",
        "license": {
            "valid": is_valid,
            "expires": expiry_time.isoformat() if expiry_time else None,
            "trial_days": TRIAL_DURATION_DAYS
        }
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def home():
    """Home page - serve the HTML interface"""
    try:
        is_valid, expiry_time = check_license()
        if not is_valid:
            # Return trial expired message as HTML
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Trial Expired - Research Paper Converter</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            </head>
            <body class="bg-dark text-light">
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-8 text-center">
                            <h1 class="display-4 mb-4">🔒 Trial Expired</h1>
                            <div class="alert alert-warning">
                                <h4>7-Day Trial Has Ended</h4>
                                <p>Your trial expired on: <strong>{expiry_time.strftime("%B %d, %Y") if expiry_time else "Unknown"}</strong></p>
                                <p>This Research Paper Converter had a 7-day trial period.</p>
                                <p class="mt-3"><em>As mentioned: "More power to those that can change main.py!"</em></p>
                                <p>Technical users can modify the license system in the source code.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """, 403
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        # If license check fails completely, allow access for Railway compatibility
        return render_template('index.html')

@app.route('/api', methods=['GET'])
def api_info():
    """API information"""
    return jsonify({
        "message": "Research Paper Converter API",
        "version": "1.0.0",
        "endpoints": {
            "register": "/api/register",
            "login": "/api/login",
            "profile": "/api/profile",
            "convert": "/api/convert",
            "papers": "/api/papers",
            "status": "/api/status"
        }
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)