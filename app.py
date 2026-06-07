from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from models import db, User, Conversation, Message, Sentiment, Emotion, Ticket, Agent, TicketActivity
from chatbot import SentimentChatbot
from datetime import datetime, timedelta
from functools import wraps
import os
import csv
import io
import sqlalchemy as sa
from sqlalchemy import inspect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'midnight-teal-premium-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sentiment_chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db, render_as_batch=True)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

chatbot = SentimentChatbot()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        u = current_user.username if current_user.is_authenticated else "Anon"
        r = current_user.role if current_user.is_authenticated else "None"
        print(f"--- SECURITY CHECK: Admin Required ---")
        print("Logged User:", u)
        print("Role:", r)
        print("Requested URL:", request.path)

        if not current_user.is_authenticated or current_user.role != 'admin':
            print("Redirecting to: /chat (Admin access required)")
            flash('Admin access required.', 'error')
            return redirect(url_for('chat'))
        
        print("Access Granted.")
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        u = current_user.username if current_user.is_authenticated else "Anon"
        r = current_user.role if current_user.is_authenticated else "None"
        print(f"--- SECURITY CHECK: User Required ---")
        print("Logged User:", u)
        print("Role:", r)
        print("Requested URL:", request.path)

        if not current_user.is_authenticated or current_user.role != 'user':
            print("Redirecting to: /admin/dashboard (User access required)")
            flash('User access required.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        print("Access Granted.")
        return f(*args, **kwargs)
    return decorated_function

def validate_db_schema():
    """Validates that all required columns exist in the Ticket table."""
    with app.app_context():
        inspector = inspect(db.engine)
        if 'tickets' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('tickets')]
            required = ['assigned_agent_id', 'status', 'resolved_at', 'closed_at', 'priority']
            missing = [r for r in required if r not in columns]
            if missing:
                print(f"CRITICAL: Missing columns in 'tickets' table: {', '.join(missing)}")
                print("Please run: flask db migrate -m 'Fix schema' && flask db upgrade")
                return False
        return True

# ... (rest of helper functions)

# --- User Panel Routes ---

@app.route('/dashboard')
@login_required
@user_required
def dashboard():
    """User-specific dashboard showing their own tickets."""
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    return render_template('user_dashboard.html', tickets=tickets)

@app.route('/my-tickets')
@login_required
@user_required
def my_tickets():
    status_filter = request.args.get('status', '')
    query = Ticket.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template('my_tickets.html', tickets=tickets)

@app.route('/profile')
@login_required
@user_required
def profile():
    return render_template('profile.html', user=current_user)

# --- Administrative Actions ---

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # ... (existing logic)
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    sentiment_filter = request.args.get('sentiment', '')
    emotion_filter = request.args.get('emotion', '')
    
    query = Ticket.query
    if search_query:
        query = query.filter(Ticket.ticket_number.ilike(f"%{search_query}%"))
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if sentiment_filter:
        query = query.filter_by(sentiment=sentiment_filter)
    if emotion_filter:
        query = query.filter_by(emotion=emotion_filter)

    pagination = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    recent_tickets = pagination.items

    # 2. KPI Stats
    total_users = User.query.count()
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter(Ticket.status.in_(['Open', 'In Progress'])).count()
    closed_tickets = Ticket.query.filter(Ticket.status.in_(['Resolved', 'Closed'])).count()
    high_priority = Ticket.query.filter(Ticket.priority.in_(['Critical', 'High'])).count()
    
    # 3. Performance Metrics
    resolved_tickets = Ticket.query.filter(Ticket.resolved_at.isnot(None)).all()
    avg_res_time = "N/A"
    if resolved_tickets:
        diffs = [(t.resolved_at - t.created_at).total_seconds() for t in resolved_tickets]
        avg_res_time = f"{round(sum(diffs) / len(diffs) / 3600, 1)} hrs"

    # 4. CSAT Logic
    total_user_msgs = Message.query.filter_by(sender='user').count()
    pos_user_msgs = Sentiment.query.join(Message).filter(Message.sender == 'user', Sentiment.sentiment == 'positive').count()
    csat = round((pos_user_msgs / total_user_msgs * 100) if total_user_msgs > 0 else 100, 1)
    
    return render_template('dashboard.html', 
        total_users=total_users, total_tickets=total_tickets, open_tickets=open_tickets,
        closed_tickets=closed_tickets, high_priority=high_priority, csat=csat,
        avg_res_time=avg_res_time, recent_tickets=recent_tickets, pagination=pagination,
        search=search_query, status_f=status_filter, priority_f=priority_filter,
        sentiment_f=sentiment_filter, emotion_f=emotion_filter)

@app.route('/api/ticket/<int:ticket_id>')
@login_required
@admin_required
def get_ticket_details(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify({
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'user': ticket.customer.username,
        'description': ticket.issue_description,
        'sentiment': ticket.sentiment,
        'emotion': ticket.emotion,
        'priority': ticket.priority,
        'status': ticket.status,
        'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'resolved_at': ticket.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.resolved_at else None
    })

@app.route('/update_ticket_status/<int:ticket_id>/<string:new_status>', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id, new_status):
    ticket = Ticket.query.get_or_404(ticket_id)
    valid_statuses = ['Open', 'In Progress', 'Resolved', 'Closed']
    if new_status in valid_statuses:
        old_status = ticket.status
        ticket.status = new_status
        if new_status == 'Resolved':
            ticket.resolved_at = datetime.utcnow()
        if new_status == 'Closed':
            ticket.closed_at = datetime.utcnow()
        
        activity = TicketActivity(
            ticket_id=ticket.id, 
            activity_type='Status Change', 
            description=f"Status updated from {old_status} to {new_status}"
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid status'}), 400

@app.route('/api/analytics')
@login_required
@admin_required
def api_analytics():
    # Sentiment Distribution
    sentiments = db.session.query(Ticket.sentiment, sa.func.count(Ticket.id)).group_by(Ticket.sentiment).all()
    sentiment_data = {
        'labels': [s[0].capitalize() if s[0] else 'Unknown' for s in sentiments],
        'values': [s[1] for s in sentiments]
    }

    # Emotion Distribution
    emotions = db.session.query(Ticket.emotion, sa.func.count(Ticket.id)).group_by(Ticket.emotion).all()
    emotion_data = {
        'labels': [e[0].capitalize() if e[0] else 'Unknown' for e in emotions],
        'values': [e[1] for e in emotions]
    }

    # Ticket Status Distribution
    statuses = db.session.query(Ticket.status, sa.func.count(Ticket.id)).group_by(Ticket.status).all()
    status_data = {
        'labels': [s[0] for s in statuses],
        'values': [s[1] for s in statuses]
    }

    return jsonify({
        'sentiment': sentiment_data,
        'emotion': emotion_data,
        'status': status_data
    })

@app.route('/api/analytics/advanced')
@login_required
def api_analytics_advanced():
    # Volume Trends (Daily - Last 14 days)
    today = datetime.utcnow().date()
    labels, volumes, resolutions = [], [], []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        v = Ticket.query.filter(sa.func.date(Ticket.created_at) == day).count()
        r = Ticket.query.filter(sa.func.date(Ticket.resolved_at) == day).count()
        labels.append(day.strftime('%b %d'))
        volumes.append(v)
        resolutions.append(r)
        
    # Priority Distribution
    priorities = db.session.query(Ticket.priority, sa.func.count(Ticket.id)).group_by(Ticket.priority).all()
    priority_data = {'labels': [p[0] for p in priorities], 'values': [p[1] for p in priorities]}

    return jsonify({
        'trends': {'labels': labels, 'volumes': volumes, 'resolutions': resolutions},
        'priority': priority_data
    })

# --- Ticket Management ---

@app.route('/admin/resolve_ticket/<int:ticket_id>', methods=['POST'])
@login_required
@admin_required
def resolve_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.status == 'Open' or ticket.status == 'In Progress':
        ticket.status = 'Closed'
        ticket.resolved_at = datetime.utcnow()
        ticket.closed_at = datetime.utcnow()
        
        activity = TicketActivity(
            ticket_id=ticket.id, 
            activity_type='Resolution', 
            description="Ticket resolved and closed via dashboard."
        )
        db.session.add(activity)
        db.session.commit()
        flash(f'Ticket {ticket.ticket_number} resolved successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/tickets')
@login_required
@admin_required
def tickets_list():
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    
    query = Ticket.query
    if status_filter: query = query.filter_by(status=status_filter)
    if priority_filter: query = query.filter_by(priority=priority_filter)
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    agents = Agent.query.filter_by(is_active=True).all()
    
    return render_template('tickets.html', tickets=tickets, agents=agents)

@app.route('/admin/ticket/<int:ticket_id>')
@login_required
@admin_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    # Get conversation history based on issue description match (simplification for prototype)
    conversation = Conversation.query.filter_by(user_id=ticket.user_id).order_by(Conversation.started_at.desc()).first()
    agents = Agent.query.filter_by(is_active=True).all()
    return render_template('ticket_detail.html', ticket=ticket, conversation=conversation, agents=agents)

@app.route('/admin/update_ticket', methods=['POST'])
@login_required
@admin_required
def update_ticket():
    ticket_id = request.form.get('ticket_id')
    new_status = request.form.get('status')
    new_priority = request.form.get('priority')
    agent_id = request.form.get('agent_id')
    
    ticket = Ticket.query.get(ticket_id)
    if not ticket: return jsonify({'error': 'Not found'}), 404
    
    changes = []
    if new_status and ticket.status != new_status:
        changes.append(f"Status changed from {ticket.status} to {new_status}")
        ticket.status = new_status
        if new_status == 'Resolved': ticket.resolved_at = datetime.utcnow()
        if new_status == 'Closed': ticket.closed_at = datetime.utcnow()
        
    if new_priority and ticket.priority != new_priority:
        changes.append(f"Priority changed from {ticket.priority} to {new_priority}")
        ticket.priority = new_priority
        
    if agent_id:
        agent = Agent.query.get(agent_id)
        if agent and ticket.assigned_agent_id != agent.id:
            changes.append(f"Assigned to {agent.name}")
            ticket.assigned_agent_id = agent.id
            
    if changes:
        activity = TicketActivity(ticket_id=ticket.id, activity_type='System Update', description="; ".join(changes))
        db.session.add(activity)
        db.session.commit()
        flash('Ticket updated successfully', 'success')
        
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

# --- Chat & Core Logic ---

@app.route('/chat')
@login_required
@user_required
def chat():
    conversation = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.started_at.desc()).first()
    if not conversation:
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
    return render_template('chat.html', conversation_id=conversation.id)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    msg_text = data.get('message', '').strip()
    conv_id = data.get('conversation_id')
    if not msg_text: return jsonify({'error': 'Empty'}), 400
    
    # 1. Analysis
    sentiment, s_conf = chatbot.predict_sentiment(msg_text)
    emotion, e_conf = chatbot.predict_emotion(msg_text)
    
    # 2. Save User Msg & Analysis
    user_msg = Message(conversation_id=conv_id, sender='user', message=msg_text)
    db.session.add(user_msg)
    db.session.flush()
    db.session.add(Sentiment(message_id=user_msg.id, sentiment=sentiment, confidence_score=s_conf))
    db.session.add(Emotion(message_id=user_msg.id, emotion=emotion, confidence=e_conf))
    
    # 3. Smart Ticket Logic
    ticket_num = None
    priority = None
    complaint_keywords = ["refund", "broken", "working", "issue", "problem", "defect", "fail", "delivery"]
    is_complaint = any(k in msg_text.lower() for k in complaint_keywords)
    
    if (sentiment == 'negative' or is_complaint) and sentiment != 'positive':
        priority = chatbot.get_auto_priority(sentiment, emotion)
        ticket_num = generate_ticket_number()
        new_ticket = Ticket(
            ticket_number=ticket_num, user_id=current_user.id, 
            issue_description=msg_text, sentiment=sentiment, emotion=emotion, 
            priority=priority, status='Open'
        )
        db.session.add(new_ticket)
        db.session.flush()
        # Initial activity
        db.session.add(TicketActivity(ticket_id=new_ticket.id, activity_type='Creation', description="Ticket auto-generated by AI"))
    
    # 4. Bot Response
    bot_reply = chatbot.get_smart_response(msg_text, sentiment, ticket_num, priority)
    bot_msg = Message(conversation_id=conv_id, sender='bot', message=bot_reply)
    db.session.add(bot_msg)
    db.session.commit()
    
    return jsonify({
        'user_message': {
            'text': msg_text, 'sentiment': sentiment, 'emotion': emotion, 
            'confidence': round(max(s_conf, e_conf) * 100, 2), 
            'ticket': ticket_num, 'timestamp': user_msg.timestamp.strftime('%H:%M')
        },
        'bot_message': {'text': bot_reply, 'timestamp': bot_msg.timestamp.strftime('%H:%M')}
    })

# --- Boilerplate ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        # Normalize selected role from form (user/admin)
        selected_role = request.form.get('role', '').strip().lower()
        
        user = User.query.filter_by(email=email).first()
        
        # DEBUG INFO (Console only)
        db_role = user.role.strip().lower() if user and user.role else 'none'
        print(f"--- LOGIN DEBUG ---")
        print(f"Email: {email}")
        print(f"Form Role: {selected_role}")
        print(f"DB Role: {db_role}")
        
        if user and check_password_hash(user.password_hash, password):
            # Normalization check for roles
            db_role = user.role.strip().lower() if user.role else 'user'
            
            # 1. Access Denied: User selected Admin but DB says they are a User
            if selected_role == 'admin' and db_role != 'admin':
                print("Result: ACCESS DENIED (Role Mismatch)")
                flash('Access Denied: You do not have Administrative privileges.', 'error')
                return render_template('login.html')
            
            # 2. Success: Proceed with Login
            login_user(user)
            print(f"Result: LOGIN SUCCESS (Role: {db_role})")
            
            if db_role == 'admin' and selected_role == 'admin':
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Logged in as {user.username}', 'success')
                return redirect(url_for('chat'))

                
        print("Result: LOGIN FAILED (Invalid Credentials)")
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username')
        e = request.form.get('email')
        p = request.form.get('password')
        
        # 1. Check if username exists
        if User.query.filter_by(username=u).first():
            flash('Username already exists. Please choose another username.', 'error')
            return redirect(url_for('register'))
            
        # 2. Check if email exists
        if User.query.filter_by(email=e).first():
            flash('Email already registered. Please login instead.', 'error')
            return redirect(url_for('register'))
            
        try:
            # Default role is 'user'
            new_user = User(
                username=u, 
                email=e, 
                password_hash=generate_password_hash(p, method='scrypt'), 
                role='user'
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as err:
            db.session.rollback()
            print(f"Registration Error: {err}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/get_messages/<int:conversation_id>')
@login_required
def get_messages(conversation_id):
    messages = Message.query.filter_by(conversation_id=conversation_id).all()
    return jsonify([{
        'sender': m.sender, 'message': m.message, 'timestamp': m.timestamp.strftime('%H:%M'),
        'sentiment': m.sentiment.sentiment if m.sentiment else None,
        'emotion': m.emotion.emotion if m.emotion else None,
        'ticket': Ticket.query.filter_by(issue_description=m.message).first().ticket_number if m.sender == 'user' and Ticket.query.filter_by(issue_description=m.message).first() else None
    } for m in messages])

if __name__ == '__main__':
    if validate_db_schema():
        with app.app_context():
            db.create_all()
            # Seed an agent if none exist
            if not Agent.query.first():
                db.session.add(Agent(name="System Admin", email="admin@sentix.ai", role="Lead Support"))
                db.session.commit()
        app.run(debug=True)
    else:
        print("Application failed to start due to schema mismatch.")
