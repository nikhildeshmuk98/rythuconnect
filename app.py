
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)

from flask_mysqldb import MySQL
import MySQLdb.cursors
from MySQLdb.cursors import DictCursor

from werkzeug.utils import secure_filename
from models import db, User
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit, join_room, leave_room
from duckduckgo_search import DDGS

import os
import requests
import datetime
import ollama
import time
import uuid
import re


# =====================================================
# FLASK APPLICATION
# =====================================================

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is missing"
    )

socketio = SocketIO(app)


# =====================================================
# EMAIL CONFIGURATION
# =====================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")

mail = Mail(app)


# =====================================================
# WEATHER API CONFIGURATION
# =====================================================

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")


# =====================================================
# GET WEATHER FUNCTION
# =====================================================

def get_weather(village, district, state, country):
    try:
        city = district

        if not WEATHER_API_KEY:
            raise RuntimeError("WEATHER_API_KEY is missing")

        url = "https://api.weatherapi.com/v1/current.json"

        response = requests.get(
            url,
            params={
                "key": WEATHER_API_KEY,
                "q": city,
                "aqi": "no"
            },
            timeout=15
        )

        data = response.json()

        if response.status_code == 200:
            current = data["current"]

            return {
                "temperature": round(current["temp_c"]),
                "condition": current["condition"]["text"],
                "humidity": current["humidity"],
                "wind": round(current["wind_kph"]),
                "visibility": str(current["vis_km"]) + " km",
                "uv": current["uv"]
            }

        app.logger.error("Weather API request failed")
        return {
            "temperature": "--",
            "condition": "Unavailable",
            "humidity": "--",
            "wind": "--",
            "visibility": "--",
            "uv": "--"
        }

    except Exception:
        app.logger.exception("Weather request failed")

        return {
            "temperature": "--",
            "condition": "Unavailable",
            "humidity": "--",
            "wind": "--",
            "visibility": "--",
            "uv": "--"
        }


# =====================================================
# AIVEN MYSQL DATABASE CONFIGURATION
# =====================================================

app.config["MYSQL_HOST"] = os.environ.get("AIVEN_MYSQL_HOST")

app.config["MYSQL_PORT"] = int(
    os.environ.get("AIVEN_MYSQL_PORT", "24029")
)

app.config["MYSQL_USER"] = os.environ.get(
    "AIVEN_MYSQL_USER", "avnadmin"
)

app.config["MYSQL_PASSWORD"] = os.environ.get(
    "AIVEN_MYSQL_PASSWORD"
)

app.config["MYSQL_DB"] = os.environ.get(
    "AIVEN_MYSQL_DB", "rythu_connect"
)

app.config["MYSQL_CONNECT_TIMEOUT"] = 15

ca_path = os.environ.get("AIVEN_MYSQL_CA")

if ca_path:
    app.config["MYSQL_SSL"] = {"ca": ca_path}

mysql = MySQL(app)


# =====================================================
# TEMPORARY DATABASE TEST ROUTE
# =====================================================
# Production deployment mundu ee route ni remove cheyyi.
# =====================================================

@app.route("/db-test")
def db_test():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE()")
        result = cur.fetchone()
        cur.close()

        return {
            "status": "connected",
            "database": result[0] if result else None
        }

    except Exception:
        app.logger.exception("Database connection failed")
        return "Database connection failed. Check application logs.", 500


# =====================================================
# EXISTING APP ROUTES CONTINUE BELOW
# =====================================================
# Nee existing routes, Socket.IO events, AI functions,
# uploads, login, posts, marketplace etc. ikkada continue avvali.


# =====================================================
# UPLOAD FOLDERS
# CLEAN & PROFESSIONAL STRUCTURE
# =====================================================

import os

# =====================================================
# BASE DIRECTORY
# =====================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

# =====================================================
# MAIN UPLOAD FOLDER
# =====================================================

BASE_UPLOAD = os.path.join(
    BASE_DIR,
    'static',
    'uploads'
)

# =====================================================
# COMMON BASE
# =====================================================

app.config['UPLOAD_FOLDER'] = BASE_UPLOAD

# =====================================================
# PROFILE IMAGES
# =====================================================

app.config['PROFILE_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'profile_images'
)
# =====================================================
# COMMUNITY CHAT FILES
# =====================================================

app.config['COMMUNITY_FILES_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'community_files'
)
# =====================================================
# COMMUNITY IMAGES
# =====================================================

app.config['COMMUNITY_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'communities'
)

# =====================================================
# POST IMAGES
# =====================================================

app.config['POST_IMAGE_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'post_images'
)

# =====================================================
# POST VIDEOS
# =====================================================

app.config['POST_VIDEO_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'post_videos'
)

# =====================================================
# MARKETPLACE
# =====================================================

app.config['MARKETPLACE_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'marketplace'
)

# =====================================================
# JOBS
# =====================================================

app.config['JOB_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'jobs'
)

# =====================================================
# BANNERS
# =====================================================

app.config['BANNER_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'banners'
)

# =====================================================
# DISEASE DETECTION
# =====================================================

app.config['DISEASE_UPLOAD_FOLDER'] = os.path.join(
    BASE_UPLOAD,
    'disease_detection'
)

# =====================================================
# AUTO CREATE FOLDERS
# =====================================================

folders = [

    app.config['UPLOAD_FOLDER'],

    app.config['PROFILE_UPLOAD_FOLDER'],

    app.config['COMMUNITY_UPLOAD_FOLDER'],

    app.config['POST_IMAGE_UPLOAD_FOLDER'],

    app.config['POST_VIDEO_UPLOAD_FOLDER'],

    app.config['MARKETPLACE_UPLOAD_FOLDER'],

    app.config['JOB_UPLOAD_FOLDER'],

    app.config['BANNER_UPLOAD_FOLDER'],

    app.config['DISEASE_UPLOAD_FOLDER'],

    app.config['COMMUNITY_FILES_UPLOAD_FOLDER']

]


# =====================================================
# CREATE IF NOT EXISTS
# =====================================================

for folder in folders:

    os.makedirs(folder, exist_ok=True)

# =====================================================
# MAX FILE SIZE (OPTIONAL)
# =====================================================

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# 100 MB

for folder in folders:
    os.makedirs(folder, exist_ok=True)

# =====================================================
# HOME PAGE
# =====================================================
@app.route('/')
def home():

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT COUNT(*) AS total FROM users")
    farmers_count = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM posts")
    posts = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM marketplace_items")
    marketplace = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM jobs")
    jobs = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM communities")
    communities = cur.fetchone()['total']

    cur.execute("""
        SELECT
            id,
            full_name,
            bio,
            phone,
            profession,
            state,
            village,
            profile_image
        FROM users
        ORDER BY followers_count DESC, posts_count DESC, id DESC
        LIMIT 6
    """)

    farmers = cur.fetchall()
    cur.close()

    return render_template(
        'index.html',
        farmers=farmers,
        farmers_count=farmers_count,
        posts=posts,
        marketplace=marketplace,
        jobs=jobs,
        communities=communities
    )
@app.route('/features')
def features():
    return render_template('features.html')
@app.route('/team')
def team():
    return render_template('team.html')
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        subject = request.form.get('subject')
        message = request.form['message']

        msg = Message(
            subject=f"Rythu Connect Contact: {subject}",
            recipients=['supportrythuconnect@gmail.com']
        )

        msg.body = f"""
New Contact Message from Rythu Connect

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}
"""

        mail.send(msg)

        flash("Message sent successfully!", "success")
        return redirect('/contact')

    return render_template("contact.html")

# =====================================================
# REGISTER PAGE
# =====================================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        profession = request.form['profession']

        village = request.form['village']
        mandal = request.form['mandal']
        district = request.form['district']
        state = request.form['state']
        country = request.form['country']
        pincode = request.form['pincode']

        skills = request.form['skills']
        bio = request.form['bio']

        profile_image = request.files['profile_image']

        image_name = 'default_profile.png'

        if profile_image:
            image_name = secure_filename(profile_image.filename)
            profile_image.save(os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], image_name))

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO users(
                full_name,
                username,
                email,
                mobile,
                password,
                profession,
                village,
                mandal,
                district,
                state,
                country,
                pincode,
                skills,
                bio,
                profile_image
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            full_name,
            username,
            email,
            mobile,
            password,
            profession,
            village,
            mandal,
            district,
            state,
            country,
            pincode,
            skills,
            bio,
            image_name
        ))

        mysql.connection.commit()
        cur.close()

        flash('Registration Successful')
        return redirect(url_for('login'))

    return render_template('register.html')


# =====================================================
# LOGIN PAGE
# =====================================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))

        user = cur.fetchone()

        cur.close()

        if user:

            session['user_id'] = user[0]
            session['username'] = user[2]
            session['profile_image'] = user[15]
            session['profession'] = user[6]

            if email == 'admin@gmail.com' and password == 'admin123':
                return redirect(url_for('admin_dashboard'))

            return redirect(url_for('rythu_dashboard'))

        else:
            flash('Invalid Credentials')
            return redirect(url_for('login'))

    return render_template('login.html')


# =====================================================
# LOGOUT
# =====================================================

@app.route('/logout')
def logout():

    session.clear()
    return redirect(url_for('home'))
@app.route('/notifications')
def notifications():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT * 
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 100
    """, (session['user_id'],))

    notifications = cur.fetchall()

    # mark all as read (Instagram style)
    cur.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = %s
    """, (session['user_id'],))

    mysql.connection.commit()
    cur.close()

    return render_template('notifications.html', notifications=notifications)
# =====================================================
# RYTHU DASHBOARD
# =====================================================

@app.route('/rythu_dashboard')
def rythu_dashboard():

    # =====================================================
    # CHECK LOGIN
    # =====================================================

    if 'user_id' not in session:
        return redirect(url_for('login'))

    logged_user_id = session['user_id']

    # =====================================================
    # DATABASE CURSOR
    # =====================================================

    cur = mysql.connection.cursor(DictCursor)

    # =====================================================
    # LOGGED USER DETAILS
    # =====================================================

    cur.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """, (logged_user_id,))

    user = cur.fetchone()

    # =====================================================
    # ALL POSTS WITH USER DETAILS
    # =====================================================

    cur.execute("""

        SELECT

            posts.*,

            users.username,
            users.profile_image,
            users.profession,

            COALESCE((
                SELECT COUNT(*)
                FROM post_likes
                WHERE post_likes.post_id = posts.id
            ),0) AS likes,

            COALESCE((
                SELECT COUNT(*)
                FROM comments
                WHERE comments.post_id = posts.id
            ),0) AS comments_count,

            COALESCE((
                SELECT COUNT(*)
                FROM post_shares
                WHERE post_shares.post_id = posts.id
            ),0) AS shares_count,

            COALESCE((
                SELECT COUNT(*)
                FROM post_saves
                WHERE post_saves.post_id = posts.id
            ),0) AS saves_count,

            EXISTS(
                SELECT 1
                FROM post_likes
                WHERE post_likes.post_id = posts.id
                AND post_likes.user_id = %s
            ) AS is_liked,

            EXISTS(
                SELECT 1
                FROM post_saves
                WHERE post_saves.post_id = posts.id
                AND post_saves.user_id = %s
            ) AS is_saved,

            EXISTS(
                SELECT 1
                FROM followers
                WHERE followers.follower_id = %s
                AND followers.following_id = posts.user_id
            ) AS is_following

        FROM posts

        JOIN users
        ON posts.user_id = users.id

        ORDER BY posts.id DESC

    """, (

        logged_user_id,
        logged_user_id,
        logged_user_id

    ))

    posts = cur.fetchall()

    # =====================================================
    # POST IMAGES + COMMENTS
    # =====================================================

    for post in posts:

        # =================================================
        # POST IMAGES
        # =================================================

        cur.execute("""

            SELECT image_path

            FROM post_images

            WHERE post_id=%s

        """, (post['id'],))

        post_images = cur.fetchall()

        post['images'] = post_images if post_images else []

        # =================================================
        # COMMENTS
        # =================================================

        cur.execute("""

            SELECT

                comments.*,

                users.username,
                users.profile_image

            FROM comments

            JOIN users
            ON comments.user_id = users.id

            WHERE comments.post_id=%s

            ORDER BY comments.id DESC

        """, (post['id'],))

        comments = cur.fetchall()

        post['comments_list'] = comments if comments else []

        # =================================================
        # SAFETY DEFAULTS
        # =================================================

        post['video'] = post.get('video', None)
        post['content'] = post.get('content', '')
        post['likes'] = post.get('likes', 0)
        post['comments_count'] = post.get('comments_count', 0)
        post['shares_count'] = post.get('shares_count', 0)
        post['saves_count'] = post.get('saves_count', 0)

    # =====================================================
    # TOTAL POSTS
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_posts

        FROM posts

        WHERE user_id=%s

    """, (logged_user_id,))

    total_posts = cur.fetchone()['total_posts']

    # =====================================================
    # FOLLOWERS COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_followers

        FROM followers

        WHERE following_id=%s

    """, (logged_user_id,))

    followers = cur.fetchone()['total_followers']

    # =====================================================
    # FOLLOWING COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_following

        FROM followers

        WHERE follower_id=%s

    """, (logged_user_id,))

    following = cur.fetchone()['total_following']

    # =====================================================
    # MARKETPLACE COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_marketplace

        FROM marketplace_items

    """)

    marketplace_count = cur.fetchone()['total_marketplace']

    # =====================================================
    # JOBS COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_jobs

        FROM jobs

    """)

    jobs_count = cur.fetchone()['total_jobs']

    # =====================================================
    # COMMUNITY COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_community

        FROM users

    """)

    community_count = cur.fetchone()['total_community']

    # =====================================================
    # SCHEMES COUNT
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_schemes

        FROM schemes

    """)

    schemes_count = cur.fetchone()['total_schemes']

    # =====================================================
    # WEATHER
    # =====================================================

    weather = get_weather(

        user.get('village', ''),
        user.get('district', ''),
        user.get('state', ''),
        user.get('country', '')

    )

    # =====================================================
    # TRENDING USERS
    # =====================================================

    cur.execute("""

        SELECT

            users.id,
            users.username,
            users.profile_image,
            users.profession,

            EXISTS(
                SELECT 1
                FROM followers
                WHERE followers.follower_id = %s
                AND followers.following_id = users.id
            ) AS is_following

        FROM users

        WHERE users.id != %s

        ORDER BY users.id DESC

        LIMIT 5

    """, (

        logged_user_id,
        logged_user_id

    ))

    trending_users = cur.fetchall()

    # =====================================================
    # SUGGESTED USERS
    # =====================================================

    cur.execute("""

        SELECT

            users.id,
            users.username,
            users.profile_image,
            users.profession

        FROM users

        WHERE users.id != %s

        ORDER BY RAND()

        LIMIT 5

    """, (logged_user_id,))

    suggested_users = cur.fetchall()

    # =====================================================
    # MARKETPLACE ITEMS WITH SELLER DETAILS
    # =====================================================

    cur.execute("""

        SELECT

            marketplace_items.*,

            users.username,
            users.profile_image

        FROM marketplace_items

        JOIN users
        ON marketplace_items.user_id = users.id

        ORDER BY marketplace_items.id DESC

        LIMIT 6

    """)

    marketplace_items = cur.fetchall()

    # =====================================================
    # RECENT JOBS
    # =====================================================

    cur.execute("""

        SELECT *

        FROM jobs

        ORDER BY id DESC

        LIMIT 6

    """)

    recent_jobs = cur.fetchall()

    # =====================================================
    # CLOSE CURSOR
    # =====================================================

    cur.close()

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================

    return render_template(

        'rythu_dashboard.html',

        user=user,

        posts=posts,

        total_posts=total_posts,
        followers=followers,
        following=following,

        marketplace_count=marketplace_count,
        jobs_count=jobs_count,
        community_count=community_count,
        schemes_count=schemes_count,

        weather=weather,

        trending_users=trending_users,
        suggested_users=suggested_users,

        marketplace_items=marketplace_items,
        recent_jobs=recent_jobs

    )


# =====================================================
# CREATE POST
# =====================================================

@app.route('/create_post', methods=['POST'])
def create_post():

    # =================================================
    # LOGIN CHECK
    # =================================================

    if 'user_id' not in session:
        return redirect(url_for('login'))

    # =================================================
    # FORM DATA
    # =================================================

    content = request.form.get('content', '').strip()

    video = request.files.get('video')

    images = request.files.getlist('images')

    # =================================================
    # EMPTY POST BLOCK
    # =================================================

    has_image = any(img.filename != '' for img in images)

    has_video = video and video.filename != ''

    if not content and not has_image and not has_video:
        return redirect(url_for('rythu_dashboard'))

    # =================================================
    # VIDEO NAME
    # =================================================

    video_name = None

    if has_video:

        video_name = f"{int(time.time())}_{secure_filename(video.filename)}"

        video.save(os.path.join(
            app.config['POST_VIDEO_UPLOAD_FOLDER'],
            video_name
        ))

    # =================================================
    # DATABASE CURSOR
    # =================================================

    cur = mysql.connection.cursor()

    # =================================================
    # INSERT SINGLE POST ONLY
    # =================================================

    cur.execute("""

        INSERT INTO posts(
            user_id,
            content,
            video,
            created_at
        )

        VALUES(%s,%s,%s,NOW())

    """, (

        session['user_id'],
        content,
        video_name

    ))

    mysql.connection.commit()

    # =================================================
    # GET POST ID
    # =================================================

    post_id = cur.lastrowid

    # =================================================
    # SAVE ALL IMAGES INSIDE SAME POST
    # =================================================

    for image in images:

        if image and image.filename != '':

            image_name = f"{int(time.time())}_{secure_filename(image.filename)}"

            image.save(os.path.join(
                app.config['POST_IMAGE_UPLOAD_FOLDER'],
                image_name
            ))

            cur.execute("""

                INSERT INTO post_images(
                    post_id,
                    image_path
                )

                VALUES(%s,%s)

            """, (

                post_id,
                image_name

            ))

    mysql.connection.commit()

    # =================================================
    # CLOSE CURSOR
    # =================================================

    cur.close()

    return redirect(url_for('rythu_dashboard'))
@app.route('/share_post/<int:post_id>', methods=['POST'])
def share_post(post_id):

    if 'user_id' not in session:
        return jsonify({'success': False})

    user_id = session['user_id']

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO shares(post_id,user_id)
        VALUES(%s,%s)
    """, (post_id, user_id))

    mysql.connection.commit()

    return jsonify({'success': True})
# =====================================================
# LIKE POST
# =====================================================
@app.route('/toggle_like/<int:post_id>', methods=['POST'])
def toggle_like(post_id):

    if 'user_id' not in session:
        return jsonify({'success': False})

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # already liked?
    cursor.execute("""
        SELECT * FROM post_likes
        WHERE post_id=%s AND user_id=%s
    """, (post_id, user_id))

    existing = cursor.fetchone()

    # UNLIKE
    if existing:

        cursor.execute("""
            DELETE FROM post_likes
            WHERE post_id=%s AND user_id=%s
        """, (post_id, user_id))

        mysql.connection.commit()

        liked = False

    # LIKE
    else:

        cursor.execute("""
            INSERT INTO post_likes (post_id, user_id)
            VALUES (%s, %s)
        """, (post_id, user_id))

        mysql.connection.commit()

        liked = True

    # TOTAL LIKES COUNT
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM post_likes
        WHERE post_id=%s
    """, (post_id,))

    total_likes = cursor.fetchone()['total']

    return jsonify({
        'success': True,
        'liked': liked,
        'total_likes': total_likes
    })

# =====================================================
# COMMENT POST
# =====================================================

# ======================================================
# ADD COMMENT
# ======================================================

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):

    # LOGIN CHECK
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # GET COMMENT FROM FORM
    comment = request.form.get('comment')

    # EMPTY COMMENT CHECK
    if not comment:
        return redirect(url_for('rythu_dashboard'))

    # DATABASE CURSOR
    cur = mysql.connection.cursor()

    # INSERT COMMENT
    cur.execute("""

        INSERT INTO comments
        (post_id, user_id, comment_text)

        VALUES (%s, %s, %s)

    """, (

        post_id,
        session['user_id'],
        comment

    ))

    mysql.connection.commit()

    cur.close()

    # REDIRECT
    return redirect(url_for('rythu_dashboard'))

# =====================================================
# SAVE POST
# =====================================================

@app.route('/toggle_save/<int:post_id>', methods=['POST'])
def toggle_save(post_id):

    if 'user_id' not in session:
        return jsonify({'success': False})

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT * FROM saved_posts
        WHERE post_id=%s AND user_id=%s
    """, (post_id, user_id))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            DELETE FROM saved_posts
            WHERE post_id=%s AND user_id=%s
        """, (post_id, user_id))

        saved = False

    else:

        cursor.execute("""
            INSERT INTO saved_posts(post_id,user_id)
            VALUES(%s,%s)
        """, (post_id, user_id))

        saved = True

    mysql.connection.commit()

    return jsonify({
        'success': True,
        'saved': saved
    })
@app.route('/toggle_follow/<int:user_id>', methods=['POST'])
def toggle_follow(user_id):

    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'})

    current_user = session['user_id']

    if current_user == user_id:
        return jsonify({'success': False, 'message': 'Invalid action'})

    conn = mysql.connection
    cursor = conn.cursor()

    # check existing follow
    cursor.execute("""
        SELECT 1 FROM followers
        WHERE follower_id=%s AND following_id=%s
    """, (current_user, user_id))

    existing = cursor.fetchone()

    # =========================
    # UNFOLLOW
    # =========================
    if existing:
        cursor.execute("""
            DELETE FROM followers
            WHERE follower_id=%s AND following_id=%s
        """, (current_user, user_id))

        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'following': False
        })

    # =========================
    # FOLLOW
    # =========================
    else:
        cursor.execute("""
            INSERT INTO followers(follower_id, following_id)
            VALUES(%s, %s)
        """, (current_user, user_id))

        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'following': True
        })

# =====================================================
# PROFILE PAGE
# =====================================================

@app.route('/profile')
def profile():

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # =====================================================
    # DATABASE CURSOR
    # =====================================================

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =====================================================
    # USER DETAILS
    # =====================================================

    cursor.execute("""

        SELECT *
        FROM users
        WHERE id = %s

    """, (user_id,))

    user = cursor.fetchone()

    # =====================================================
    # USER POSTS
    # =====================================================

    cursor.execute("""

        SELECT

            posts.*,

            (
                SELECT COUNT(*)
                FROM post_likes
                WHERE post_likes.post_id = posts.id
            ) AS likes,

            (
                SELECT COUNT(*)
                FROM comments
                WHERE comments.post_id = posts.id
            ) AS comments,

            (
                SELECT COUNT(*)
                FROM shares
                WHERE shares.post_id = posts.id
            ) AS shares,

            (
                SELECT COUNT(*)
                FROM saved_posts
                WHERE saved_posts.post_id = posts.id
            ) AS saves

        FROM posts

        WHERE posts.user_id = %s

        ORDER BY posts.created_at DESC

    """, (user_id,))

    posts = cursor.fetchall()

    # =====================================================
    # FETCH POST IMAGES
    # =====================================================

    for post in posts:

        cursor.execute("""

            SELECT image_path
            FROM post_images
            WHERE post_id = %s

        """, (post['id'],))

        post['images'] = cursor.fetchall()

    # =====================================================
    # USER MARKETPLACE ITEMS
    # =====================================================

    cursor.execute("""

        SELECT *
        FROM marketplace_items
        WHERE user_id = %s
        ORDER BY created_at DESC

    """, (user_id,))

    marketplace_items = cursor.fetchall()

    # =====================================================
    # FOLLOWERS COUNT
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total
        FROM followers
        WHERE following_id = %s

    """, (user_id,))

    followers = cursor.fetchone()['total']

    # =====================================================
    # FOLLOWING COUNT
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total
        FROM followers
        WHERE follower_id = %s

    """, (user_id,))

    following = cursor.fetchone()['total']

    # =====================================================
    # TOTAL POSTS
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total
        FROM posts
        WHERE user_id = %s

    """, (user_id,))

    total_posts = cursor.fetchone()['total']

    # =====================================================
    # TOTAL LIKES
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total

        FROM post_likes pl

        JOIN posts p
        ON pl.post_id = p.id

        WHERE p.user_id = %s

    """, (user_id,))

    total_likes = cursor.fetchone()['total']

    # =====================================================
    # TOTAL COMMENTS
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total

        FROM comments c

        JOIN posts p
        ON c.post_id = p.id

        WHERE p.user_id = %s

    """, (user_id,))

    total_comments = cursor.fetchone()['total']

    # =====================================================
    # TOTAL SHARES
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total

        FROM shares s

        JOIN posts p
        ON s.post_id = p.id

        WHERE p.user_id = %s

    """, (user_id,))

    total_shares = cursor.fetchone()['total']

    # =====================================================
    # TOTAL MARKETPLACE ITEMS
    # =====================================================

    cursor.execute("""

        SELECT COUNT(*) AS total
        FROM marketplace_items
        WHERE user_id = %s

    """, (user_id,))

    total_items = cursor.fetchone()['total']

    # =====================================================
    # CLOSE CURSOR
    # =====================================================

    cursor.close()

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================

    return render_template(

        'profile.html',

        user=user,

        posts=posts,
        marketplace_items=marketplace_items,

        followers=followers,
        following=following,

        total_posts=total_posts,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        total_items=total_items

    )

# =====================================================
# EDIT MARKETPLACE ITEM
# =====================================================

# =====================================================
# EDIT MARKETPLACE ITEM
# =====================================================

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_marketplace_item(item_id):

    # LOGIN CHECK
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =====================================================
    # FETCH USER
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    # =====================================================
    # FETCH ITEM
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM marketplace_items
        WHERE id = %s AND user_id = %s
    """, (item_id, user_id))

    item = cursor.fetchone()

    if not item:
        flash('Item not found!', 'danger')
        return redirect('/profile')

    # =====================================================
    # UPDATE ITEM
    # =====================================================

    if request.method == 'POST':

        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description')

        unit_type = request.form.get('unit_type')
        category = request.form.get('category')

        village = request.form.get('village')
        mandal = request.form.get('mandal')
        district = request.form.get('district')
        state = request.form.get('state')
        country = request.form.get('country')
        pincode = request.form.get('pincode')

        image = item['image']

        # =====================================================
        # IMAGE UPDATE
        # =====================================================

        if 'image' in request.files:

            file = request.files['image']

            if file and file.filename != '':

                filename = secure_filename(file.filename)

                unique_name = f"{uuid.uuid4().hex}_{filename}"

                save_path = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    'marketplace',
                    unique_name
                )

                file.save(save_path)

                # DELETE OLD IMAGE
                if image:

                    old_path = os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        'marketplace',
                        image
                    )

                    if os.path.exists(old_path):
                        os.remove(old_path)

                image = unique_name

        # =====================================================
        # UPDATE DATABASE
        # =====================================================

        cursor.execute("""

            UPDATE marketplace_items

            SET
                title = %s,
                description = %s,
                price = %s,
                unit_type = %s,
                category = %s,
                village = %s,
                mandal = %s,
                district = %s,
                state = %s,
                country = %s,
                pincode = %s,
                image = %s

            WHERE id = %s

        """, (

            title,
            description,
            price,
            unit_type,
            category,

            village,
            mandal,
            district,
            state,
            country,
            pincode,

            image,
            item_id

        ))

        mysql.connection.commit()

        flash('Marketplace item updated successfully!', 'success')

        return redirect('/profile')

    cursor.close()

    # =====================================================
    # RENDER PAGE
    # =====================================================

    return render_template(
        'edit_item.html',
        item=item,
        user=user
    )
# =====================================================
# EDIT PROFILE
# =====================================================

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():

    # LOGIN CHECK
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =====================================================
    # UPDATE PROFILE
    # =====================================================

    if request.method == 'POST':

        # ================= FORM DATA =================

        full_name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('gmail')
        mobile = request.form.get('mobile')

        profession = request.form.get('profession')
        land_area = request.form.get('land_area')
        farming_experience = request.form.get('farming_experience')
        irrigation_type = request.form.get('irrigation_type')

        main_crops = request.form.get('main_crops')

        village = request.form.get('village')
        mandal = request.form.get('mandal')
        district = request.form.get('district')
        state = request.form.get('state')
        country = request.form.get('country')
        pincode = request.form.get('pincode')

        skills = request.form.get('skills')
        bio = request.form.get('bio')

        # ================= GET OLD USER =================

        cursor.execute(
            "SELECT * FROM users WHERE id=%s",
            (user_id,)
        )

        old_user = cursor.fetchone()

        # ================= OLD IMAGES =================

        profile_filename = old_user['profile_image']
        banner_filename = old_user['banner_image']

        # =====================================================
        # PROFILE IMAGE
        # =====================================================

        profile_image = request.files.get('profile_image')

        if profile_image and profile_image.filename != '':

            profile_filename = secure_filename(
                profile_image.filename
            )

            profile_path = os.path.join(
                app.config['PROFILE_UPLOAD_FOLDER'],
                profile_filename
            )

            profile_image.save(profile_path)

        # =====================================================
        # BANNER IMAGE
        # =====================================================

        banner_image = request.files.get('banner_image')

        if banner_image and banner_image.filename != '':

            banner_filename = secure_filename(
                banner_image.filename
            )

            banner_path = os.path.join(
                app.config['BANNER_UPLOAD_FOLDER'],
                banner_filename
            )

            banner_image.save(banner_path)

        # =====================================================
        # UPDATE DATABASE
        # =====================================================

        cursor.execute("""

        UPDATE users SET

        full_name=%s,
        username=%s,
        email=%s,
        mobile=%s,
        profession=%s,
        land_area=%s,
        farming_experience=%s,
        irrigation_type=%s,
        main_crops=%s,
        village=%s,
        mandal=%s,
        district=%s,
        state=%s,
        country=%s,
        pincode=%s,
        skills=%s,
        bio=%s,
        profile_image=%s,
        banner_image=%s

        WHERE id=%s

        """, (

            full_name,
            username,
            email,
            mobile,
            profession,
            land_area,
            farming_experience,
            irrigation_type,
            main_crops,
            village,
            mandal,
            district,
            state,
            country,
            pincode,
            skills,
            bio,
            profile_filename,
            banner_filename,
            user_id

        ))

        mysql.connection.commit()

        cursor.close()

        flash('Profile Updated Successfully!', 'success')

        return redirect('/profile')

    # =====================================================
    # GET USER DATA
    # =====================================================

    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.close()

    return render_template(
        'edit_profile.html',
        user=user
    )
# =====================================================
# EDIT POST
# =====================================================

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # =====================================================
    # DATABASE CURSOR
    # =====================================================

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =====================================================
    # FETCH USER
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    # =====================================================
    # FETCH POST
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM posts
        WHERE id = %s
        AND user_id = %s
    """, (post_id, user_id))

    post = cursor.fetchone()

    # =====================================================
    # POST NOT FOUND
    # =====================================================

    if not post:

        cursor.close()

        flash('Post not found', 'danger')

        return redirect(url_for('profile'))

    # =====================================================
    # FETCH POST IMAGES
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM post_images
        WHERE post_id = %s
    """, (post_id,))

    post_images = cursor.fetchall()

    # =====================================================
    # UPDATE POST
    # =====================================================

    if request.method == 'POST':

        # =====================================================
        # FORM DATA
        # =====================================================

        content = request.form.get('content')

        # =====================================================
        # UPDATE POST CONTENT
        # =====================================================

        cursor.execute("""
            UPDATE posts
            SET content = %s
            WHERE id = %s
            AND user_id = %s
        """, (
            content,
            post_id,
            user_id
        ))

        # =====================================================
        # DELETE OLD IMAGES
        # =====================================================

        delete_old = request.form.get('delete_old_images')

        if delete_old == 'yes':

            # FETCH OLD IMAGES
            cursor.execute("""
                SELECT *
                FROM post_images
                WHERE post_id = %s
            """, (post_id,))

            old_images = cursor.fetchall()

            # DELETE FILES
            for img in old_images:

                old_path = os.path.join(
                    app.config['POST_IMAGE_UPLOAD_FOLDER'],
                    img['image_path']
                )

                if os.path.exists(old_path):
                    os.remove(old_path)

            # DELETE DATABASE RECORDS
            cursor.execute("""
                DELETE FROM post_images
                WHERE post_id = %s
            """, (post_id,))

        # =====================================================
        # NEW IMAGE UPLOAD
        # =====================================================

        files = request.files.getlist('images')

        for file in files:

            if file and file.filename != '':

                filename = secure_filename(file.filename)

                save_path = os.path.join(
                    app.config['POST_IMAGE_UPLOAD_FOLDER'],
                    filename
                )

                file.save(save_path)

                # SAVE IMAGE IN DATABASE
                cursor.execute("""
                    INSERT INTO post_images (
                        post_id,
                        image_path
                    )
                    VALUES (%s, %s)
                """, (
                    post_id,
                    filename
                ))

        # =====================================================
        # COMMIT
        # =====================================================

        mysql.connection.commit()

        cursor.close()

        flash('Post updated successfully!', 'success')

        return redirect(url_for('profile'))

    # =====================================================
    # CLOSE CURSOR
    # =====================================================

    cursor.close()

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================

    return render_template(

        'edit_post.html',

        user=user,
        post=post,
        post_images=post_images

    )

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):

    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connection
    cursor = conn.cursor()

    # DELETE POST ONLY
    cursor.execute("""
        DELETE FROM posts
        WHERE id=%s
    """, (post_id,))

    conn.commit()

    cursor.close()

    return redirect('/profile')


@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM marketplace_items
        WHERE id = %s AND user_id = %s
    """, (item_id, user_id))

    item = cursor.fetchone()

    if item:

        # DELETE IMAGE
        if item['image']:

            image_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                'marketplace',
                item['image']
            )

            if os.path.exists(image_path):
                os.remove(image_path)

        # DELETE ITEM
        cursor.execute("""
            DELETE FROM marketplace_items
            WHERE id = %s
        """, (item_id,))

        mysql.connection.commit()

    cursor.close()

    flash('Item deleted permanently!', 'success')

    return redirect('/profile')
# =====================================================
# EDIT MARKETPLACE ITEM
# =====================================================

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # FETCH ITEM

    cursor.execute("""

        SELECT *
        FROM marketplace_items
        WHERE id = %s
        AND user_id = %s

    """, (item_id, user_id))

    item = cursor.fetchone()

    if not item:
        flash("Item not found", "danger")
        return redirect('/profile')

    # =====================================================
    # UPDATE ITEM
    # =====================================================

    if request.method == 'POST':

        title       = request.form.get('title')
        price       = request.form.get('price')
        description = request.form.get('description')
        unit        = request.form.get('unit')
        category    = request.form.get('category')

        village     = request.form.get('village')
        mandal      = request.form.get('mandal')
        district    = request.form.get('district')
        state       = request.form.get('state')
        country     = request.form.get('country')
        pincode     = request.form.get('pincode')

        image = item['image']

        # NEW IMAGE

        if 'image' in request.files:

            file = request.files['image']

            if file and file.filename != '':

                # DELETE OLD IMAGE

                old_path = os.path.join(
                    app.config['UPLOAD_FOLDER_MARKETPLACE'],
                    item['image']
                )

                if os.path.exists(old_path):
                    os.remove(old_path)

                # SAVE NEW IMAGE

                filename = secure_filename(file.filename)

                new_filename = f"{uuid.uuid4()}_{filename}"

                file.save(os.path.join(
                    app.config['UPLOAD_FOLDER_MARKETPLACE'],
                    new_filename
                ))

                image = new_filename

        # UPDATE DATABASE

        cursor.execute("""

            UPDATE marketplace_items

            SET

                title = %s,
                price = %s,
                description = %s,
                unit = %s,
                category = %s,

                village = %s,
                mandal = %s,
                district = %s,
                state = %s,
                country = %s,
                pincode = %s,

                image = %s

            WHERE id = %s

        """, (

            title,
            price,
            description,
            unit,
            category,

            village,
            mandal,
            district,
            state,
            country,
            pincode,

            image,
            item_id

        ))

        mysql.connection.commit()

        cursor.close()

        flash('Item updated successfully', 'success')

        return redirect('/profile')

    return render_template(
        'edit_item.html',
        item=item
    )

# =========================================================
# VIEW USER PROFILE
# =========================================================

@app.route('/view_user_profile/<int:user_id>')
def view_user_profile(user_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user_id']

    cur = mysql.connection.cursor(DictCursor)

    # =====================================================
    # PROFILE USER
    # =====================================================

    cur.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """, (user_id,))

    profile_user = cur.fetchone()

    # =====================================================
    # USER POSTS
    # =====================================================

    cur.execute("""

        SELECT

            posts.*,

            COALESCE((
                SELECT COUNT(*)
                FROM post_likes
                WHERE post_likes.post_id = posts.id
            ),0) AS likes,

            COALESCE((
                SELECT COUNT(*)
                FROM comments
                WHERE comments.post_id = posts.id
            ),0) AS comments,

            COALESCE((
                SELECT COUNT(*)
                FROM post_shares
                WHERE post_shares.post_id = posts.id
            ),0) AS shares,

            COALESCE((
                SELECT COUNT(*)
                FROM post_saves
                WHERE post_saves.post_id = posts.id
            ),0) AS saves

        FROM posts

        WHERE posts.user_id=%s

        ORDER BY posts.id DESC

    """, (user_id,))

    posts = cur.fetchall()

    # =====================================================
    # ADD POST IMAGES + VIDEOS
    # =====================================================

    for post in posts:

        # ================================================
        # POST IMAGES
        # ================================================

        cur.execute("""

            SELECT image_path

            FROM post_images

            WHERE post_id=%s

        """, (post['id'],))

        images = cur.fetchall()

        post['images'] = images if images else []

        # ================================================
        # VIDEO DEFAULT
        # ================================================

        post['video'] = post.get('video', None)

    # =====================================================
    # FOLLOWERS
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_followers

        FROM followers

        WHERE following_id=%s

    """, (user_id,))

    followers = cur.fetchone()['total_followers']

    # =====================================================
    # FOLLOWING
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_following

        FROM followers

        WHERE follower_id=%s

    """, (user_id,))

    following = cur.fetchone()['total_following']

    # =====================================================
    # TOTAL POSTS
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_posts

        FROM posts

        WHERE user_id=%s

    """, (user_id,))

    total_posts = cur.fetchone()['total_posts']

    # =====================================================
    # TOTAL LIKES
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_likes

        FROM post_likes

        WHERE post_id IN (
            SELECT id FROM posts WHERE user_id=%s
        )

    """, (user_id,))

    total_likes = cur.fetchone()['total_likes']

    # =====================================================
    # TOTAL COMMENTS
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_comments

        FROM comments

        WHERE post_id IN (
            SELECT id FROM posts WHERE user_id=%s
        )

    """, (user_id,))

    total_comments = cur.fetchone()['total_comments']

    # =====================================================
    # TOTAL SHARES
    # =====================================================

    cur.execute("""

        SELECT COUNT(*) AS total_shares

        FROM post_shares

        WHERE post_id IN (
            SELECT id FROM posts WHERE user_id=%s
        )

    """, (user_id,))

    total_shares = cur.fetchone()['total_shares']

    # =====================================================
    # MARKETPLACE ITEMS
    # =====================================================

    cur.execute("""

        SELECT *

        FROM marketplace_items

        WHERE user_id=%s

        ORDER BY id DESC

    """, (user_id,))

    marketplace_items = cur.fetchall()

    # =====================================================
    # CURRENT USER
    # =====================================================

    cur.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """, (current_user_id,))

    current_user = cur.fetchone()

    cur.close()

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================

    return render_template(

        'view_user_profile.html',

        profile_user=profile_user,
        current_user=current_user,

        posts=posts,

        followers=followers,
        following=following,

        total_posts=total_posts,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,

        marketplace_items=marketplace_items

    )
@app.route('/chat/<int:user_id>')
def chat(user_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    other_user = cursor.fetchone()

    return render_template('chat.html', other_user=other_user)
@app.route('/marketplace')
def marketplace():

    # ================= LOGIN CHECK =================
    if 'user_id' not in session:

        flash("Please login first", "warning")

        return redirect(url_for('login'))

    # ================= CURSOR =================
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =========================================================
    # FETCH MARKETPLACE ITEMS + SELLER DETAILS
    # =========================================================
    cur.execute("""

        SELECT

            marketplace_items.*,

            users.username,
            users.profile_image,
            users.phone,

            users.village AS seller_village,
            users.district AS seller_district,
            users.state AS seller_state

        FROM marketplace_items

        JOIN users
        ON marketplace_items.user_id = users.id

        ORDER BY marketplace_items.id DESC

    """)

    items = cur.fetchall()

    # =========================================================
    # CURRENT LOGGED USER
    # =========================================================
    cur.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """, (session['user_id'],))

    user = cur.fetchone()

    # =========================================================
    # TOTAL LISTINGS
    # =========================================================
    cur.execute("""

        SELECT COUNT(*) AS total_listings

        FROM marketplace_items

    """)

    total_listings = cur.fetchone()['total_listings']

    # =========================================================
    # ACTIVE FARMERS
    # =========================================================
    cur.execute("""

        SELECT COUNT(DISTINCT user_id) AS total_farmers

        FROM marketplace_items

    """)

    total_farmers = cur.fetchone()['total_farmers']

    # =========================================================
    # TOTAL CATEGORIES
    # =========================================================
    cur.execute("""

        SELECT COUNT(DISTINCT category) AS total_categories

        FROM marketplace_items

    """)

    total_categories = cur.fetchone()['total_categories']

    # =========================================================
    # SOLD ITEMS COUNT
    # =========================================================
    cur.execute("""

        SELECT COUNT(*) AS sold_items

        FROM marketplace_items

        WHERE is_sold = 1

    """)

    sold_items = cur.fetchone()['sold_items']

    # =========================================================
    # SUCCESSFUL DEALS %
    # =========================================================
    successful_deals_percentage = 0

    if total_listings > 0:

        successful_deals_percentage = round(
            (sold_items / total_listings) * 100
        )

    # =========================================================
    # CLOSE CURSOR
    # =========================================================
    cur.close()

    # =========================================================
    # RENDER TEMPLATE
    # =========================================================
    return render_template(

        'marketplace.html',

        # MAIN DATA
        items=items,
        user=user,

        # STATS
        total_listings=total_listings,
        total_farmers=total_farmers,
        total_categories=total_categories,
        sold_items=sold_items,
        successful_deals_percentage=successful_deals_percentage
    )
@app.route('/sell_item', methods=['POST'])
def sell_item():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    # FORM DATA
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')

    unit_type = request.form.get('unit')

    category = request.form.get('category')

    # LOCATION
    village = request.form.get('village')
    mandal = request.form.get('mandal')
    district = request.form.get('district')
    state = request.form.get('state')
    country = request.form.get('country')
    pincode = request.form.get('pincode')

    # IMAGE
    file = request.files.get('image')

    image_name = None

    if file and file.filename != '':

        image_name = secure_filename(file.filename)

        save_path = os.path.join(
            app.config['MARKETPLACE_UPLOAD_FOLDER'],
            image_name
        )

        file.save(save_path)

    # DATABASE INSERT
    cur = mysql.connection.cursor()

    cur.execute("""

        INSERT INTO marketplace_items
        (
            user_id,
            title,
            description,
            price,
            unit_type,
            category,
            village,
            mandal,
            district,
            state,
            country,
            pincode,
            image
        )

        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

    """, (

        session['user_id'],
        title,
        description,
        price,
        unit_type,
        category,
        village,
        mandal,
        district,
        state,
        country,
        pincode,
        image_name

    ))

    mysql.connection.commit()

    cur.close()

    flash("Item listed successfully", "success")

    return redirect(url_for('marketplace'))
# =====================================================
# AI ASSISTANT PAGE
# =====================================================
@app.route('/ai_assistant')
def ai_assistant():

    # =====================================================
    # LOGIN CHECK
    # =====================================================
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # =====================================================
    # GET USER
    # =====================================================
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT * FROM users WHERE id = %s
    """, (session['user_id'],))

    user = cur.fetchone()
    cur.close()

    # =====================================================
    # DEFAULT WEATHER (SAFE FALLBACK)
    # =====================================================
    weather = {
        "temp": "--",
        "description": "Weather unavailable",
        "humidity": "--",
        "wind": "--",
        "location": user.get('village', ''),
        "icon": ""
    }

    # =====================================================
    # WEATHER API CALL (SAFE)
    # =====================================================
    try:
        weather_data = get_weather(
            user.get('village', ''),
            user.get('district', ''),
            user.get('state', ''),
            user.get('country', '')
        )

        print("WEATHER DATA:", weather_data)

        if weather_data and 'current' in weather_data:

            weather = {
                "temp": weather_data['current'].get('temp_c', '--'),
                "description": weather_data['current']['condition'].get('text', 'N/A'),
                "humidity": weather_data['current'].get('humidity', '--'),
                "wind": weather_data['current'].get('wind_kph', '--'),
                "location": weather_data['location'].get('name', user.get('village', '')),
                "icon": "https:" + weather_data['current']['condition'].get('icon', '')
            }

    except Exception as e:
        print("Weather Error:", e)

    # =====================================================
    # (OPTIONAL) OLLAMA MODEL INFO
    # =====================================================
    try:
        import requests

        res = requests.get("http://localhost:11434/api/tags")
        data = res.json()

        models = data.get("models", [])
        ai_model = models[0]["name"] if models else "Ollama Not Found"

    except:
        ai_model = "Ollama Not Running"

    # =====================================================
    # MESSAGE COUNT (SESSION / DB EXAMPLE)
    # =====================================================
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cur.execute("""
            SELECT COUNT(*) AS msg_count
            FROM messages
            WHERE user_id = %s
        """, (session['user_id'],))

        msg_count = cur.fetchone()['msg_count']
        cur.close()

    except:
        msg_count = 0

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================
    return render_template(
        'ai_assistant.html',
        user=user,
        weather=weather,
        ai_model=ai_model,
        msg_count=msg_count
    )
# =====================================================
# AI CHATBOT API
# =====================================================

@app.route('/ai_chat', methods=['POST'])
def ai_chat():

    # ==============================
    # CHECK LOGIN
    # ==============================

    if 'user_id' not in session:

        return jsonify({
            'response': 'Please login first'
        }), 401

    try:

        # ==============================
        # GET USER MESSAGE
        # ==============================

        data = request.get_json()

        user_message = data.get('message')

        # ==============================
        # INTERNET SEARCH
        # ==============================

        internet_data = ""

        try:

            with DDGS() as ddgs:

                results = ddgs.text(
                    user_message,
                    max_results=3
                )

                for result in results:

                    internet_data += f"""

                    Title:
                    {result['title']}

                    Content:
                    {result['body']}

                    """

        except Exception as search_error:

            print("SEARCH ERROR:", search_error)

        # ==============================
        # FAST AI PROMPT
        # ==============================

        messages = [

            {
                'role': 'system',

                'content': '''

                You are Rythu Connect AI.

                You are a smart agriculture assistant.

                Answer fast, short, smart and human-like.

                Use latest internet information if available.

                Help farmers with:
                - Crops
                - Fertilizers
                - Pest control
                - Market prices
                - Weather
                - Government schemes

                '''
            },

            {
                'role': 'user',

                'content': f'''

                User Question:
                {user_message}

                Latest Internet Data:
                {internet_data}

                '''
            }

        ]

        # ==============================
        # OLLAMA FAST RESPONSE
        # ==============================

        response = ollama.chat(

            model='phi3',

            messages=messages

        )

        ai_response = response['message']['content']

        # ==============================
        # SAVE CHAT HISTORY
        # ==============================

        cur = mysql.connection.cursor()

        cur.execute("""

            INSERT INTO ai_chat_history
            (user_id, user_message, ai_response)

            VALUES(%s,%s,%s)

        """, (

            session['user_id'],
            user_message,
            ai_response

        ))

        mysql.connection.commit()

        cur.close()

        # ==============================
        # RETURN RESPONSE
        # ==============================

        return jsonify({

            'response': ai_response

        })

    except Exception as e:

        print("AI ERROR:", e)

        return jsonify({

            'response':
            'AI server error. Please try again.'

        }), 500


@app.route('/analyze_disease', methods=['POST'])
def analyze_disease():

    try:

        image = request.files['image']

        image_path = os.path.join(
            'uploads',
            image.filename
        )

        image.save(image_path)

        response = ollama.chat(

            model='qwen2.5vl:7b',

            messages=[{
                'role': 'user',
                'content': '''
You are an expert agricultural scientist.

Analyze this crop image.

Return ONLY JSON:

{
"crop_name":"",
"image_description":"",
"disease_name":"",
"severity":"",
"confidence":"",
"symptoms":"",
"cause":"",
"recommended_pesticide":"",
"dosage":"",
"application_method":"",
"fertilizer_advice":"",
"precautions":"",
"follow_up_action":""
}
''',
                'images': [image_path]
            }]
        )

        return jsonify({
            'result': response['message']['content']
        })

    except Exception as e:
        print(e)

        return jsonify({
            'error': str(e)
        })
@app.route('/detect_disease', methods=['POST'])
def detect_disease():

    try:

        image = request.files['image']

        upload_folder = "uploads"
        os.makedirs(upload_folder, exist_ok=True)

        image_path = os.path.join(
            upload_folder,
            image.filename
        )

        image.save(image_path)

        response = ollama.chat(

            model='qwen2.5vl:7b',

            messages=[{
                'role': 'user',

                'content': '''
You are an expert agricultural scientist.

Analyze this crop image carefully.

Return ONLY valid JSON.

{
"crop_name":"",
"image_description":"",
"disease_name":"",
"severity":"",
"confidence":"",
"symptoms":"",
"cause":"",
"recommended_pesticide":"",
"dosage":"",
"application_method":"",
"fertilizer_advice":"",
"precautions":"",
"follow_up_action":""
}

If plant is healthy:
"disease_name":"Healthy Plant"

Do not return markdown.
Do not return explanation.
Only JSON.
''',

                'images': [image_path]

            }]
        )

        import json

        result = response['message']['content']

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        return jsonify(json.loads(result))

    except Exception as e:

        print(e)

        return jsonify({
            "crop_name": "-",
            "disease_name": "Analysis Failed",
            "confidence": "0%",
            "error": str(e)
        })
# =========================================================
# SEARCH USERS API
# =========================================================

@app.route('/search_users')
def search_users():

    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').strip()

    cur = mysql.connection.cursor(DictCursor)

    cur.execute("""

        SELECT

            id,
            username,
            profile_image,
            profession,
            village,
            mandal,
            district,
            state,
            pincode

        FROM users

        WHERE

            username LIKE %s
            OR profession LIKE %s
            OR village LIKE %s
            OR mandal LIKE %s
            OR district LIKE %s
            OR state LIKE %s
            OR pincode LIKE %s

        ORDER BY id DESC

        LIMIT 20

    """, (

        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%"

    ))

    users = cur.fetchall()

    cur.close()

    return jsonify(users)
# =====================================================
# WEATHER PAGE
# =====================================================

@app.route('/weather_forecast')
def weather_forecast():

    # =====================================================
    # CHECK LOGIN
    # =====================================================

    if 'user_id' not in session:

        flash("Please login first", "warning")

        return redirect(url_for('login'))

    # =====================================================
    # DATABASE CURSOR
    # =====================================================

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =====================================================
    # FETCH USER
    # =====================================================

    cur.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """, (session['user_id'],))

    user = cur.fetchone()

    # =====================================================
    # LIVE WEATHER
    # =====================================================

    weather = get_weather(

        user.get('village', ''),
        user.get('district', ''),
        user.get('state', ''),
        user.get('country', '')

    )

    # =====================================================
    # FORECAST DATA
    # =====================================================

    forecast = [

        {
            "day": "Mon",
            "temp": weather['temperature'],
            "condition": weather['condition']
        },

        {
            "day": "Tue",
            "temp": weather['temperature'] - 1,
            "condition": "Cloudy"
        },

        {
            "day": "Wed",
            "temp": weather['temperature'] + 1,
            "condition": "Sunny"
        },

        {
            "day": "Thu",
            "temp": weather['temperature'] - 2,
            "condition": "Rain"
        },

        {
            "day": "Fri",
            "temp": weather['temperature'],
            "condition": "Partly Cloudy"
        },

        {
            "day": "Sat",
            "temp": weather['temperature'] + 2,
            "condition": "Sunny"
        },

        {
            "day": "Sun",
            "temp": weather['temperature'] - 1,
            "condition": "Rain"
        }

    ]

    # =====================================================
    # CLOSE CURSOR
    # =====================================================

    cur.close()

    # =====================================================
    # RENDER TEMPLATE
    # =====================================================

    return render_template(

        'weather_forecast.html',

        user=user,

        weather=weather,

        forecast=forecast

    )
# =====================================================
# JOBS PAGE
# =====================================================

@app.route('/jobs')
def jobs():

    import requests
    import re

    # ================= FETCH JOBS API =================

    url = "https://remotive.com/api/remote-jobs"

    params = {
        "search": "agriculture"
    }

    response = requests.get(url, params=params)

    data = response.json()

    jobs = []

    for item in data['jobs']:

        jobs.append({

            "id": item.get("id"),

            "job_title": item.get("title"),

            "company_name": item.get("company_name"),

            "location": item.get("candidate_required_location"),

            "salary": item.get("salary", "Not Disclosed"),

            "description": re.sub(
                '<.*?>',
                '',
                item.get("description", "")
            ),

            "job_type": item.get("job_type", "Full Time"),

            "created_at": item.get("publication_date"),

            "redirect_url": item.get("url"),

            "company_logo": item.get("company_logo")

        })

    # ================= HERO STATS =================

    total_jobs = len(jobs)

    companies = set()

    for job in jobs:
        companies.add(job["company_name"])

    total_companies = len(companies)

    placed_percentage = 86

    # ================= USER DETAILS =================

    user = None

    if 'user_id' in session:

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE id=%s",
            (session['user_id'],)
        )

        user_data = cur.fetchone()

        # COLUMN NAMES
        columns = [col[0] for col in cur.description]

        # CONVERT TUPLE TO DICTIONARY
        if user_data:
            user = dict(zip(columns, user_data))

        cur.close()

    # ================= RENDER TEMPLATE =================

    return render_template(

        "jobs.html",

        jobs=jobs,

        total_jobs=total_jobs,

        total_companies=total_companies,

        placed_percentage=placed_percentage,

        user=user

    )
# =====================================================
# POST JOB
# =====================================================

@app.route('/post_job', methods=['POST'])
def post_job():

    company_name = request.form['company_name']
    job_title = request.form['job_title']
    description = request.form['description']
    salary = request.form['salary']
    job_type = request.form['job_type']

    image = request.files['company_image']

    image_name = secure_filename(image.filename)

    image.save(os.path.join(app.config['JOB_UPLOAD_FOLDER'], image_name))

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO jobs(
            user_id,
            company_image,
            company_name,
            job_title,
            description,
            salary_range,
            job_type
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
    """, (
        session['user_id'],
        image_name,
        company_name,
        job_title,
        description,
        salary,
        job_type
    ))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('jobs'))


# =====================================================
# GOVERNMENT SCHEMES PAGE
# =====================================================

@app.route('/govt_schemes')
def govt_schemes():

    # =========================================
    # CHECK USER LOGIN
    # =========================================

    if 'user_id' not in session:

        flash('Please Login First', 'warning')

        return redirect(url_for('login'))

    # =========================================
    # DATABASE CURSOR
    # =========================================

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # =========================================
    # FETCH ALL GOVERNMENT SCHEMES
    # =========================================

    cur.execute("""

        SELECT
            id,
            scheme_name,
            category,
            description,
            eligibility,
            benefit,
            state,
            website_link,
            image_url,
            created_at

        FROM govt_schemes

        ORDER BY id DESC

    """)

    schemes = cur.fetchall()

    # =========================================
    # FETCH LOGGED-IN USER DETAILS
    # =========================================

    cur.execute("""

        SELECT *

        FROM users

        WHERE id = %s

    """, (session['user_id'],))

    user = cur.fetchone()

    # =========================================
    # CLOSE CURSOR
    # =========================================

    cur.close()

    # =========================================
    # RENDER TEMPLATE
    # =========================================

    return render_template(

        'govt_schemes.html',

        schemes=schemes,
        user=user

    )

@app.route('/community')
def community():

    # LOGIN CHECK
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # CURSOR
    cur = mysql.connection.cursor(
        MySQLdb.cursors.DictCursor
    )

    # ═══════════════════════════════════════
    # FETCH COMMUNITIES
    # ═══════════════════════════════════════

    cur.execute("""
        SELECT
            c.*,
            u.username,
            u.profile_image,

            (
                SELECT COUNT(*)
                FROM community_members cm
                WHERE cm.community_id = c.id
            ) AS member_count

        FROM communities c

        JOIN users u
        ON c.created_by = u.id

        ORDER BY c.id DESC
    """)

    communities = cur.fetchall()

    # ═══════════════════════════════════════
    # LOGGED IN USER
    # ═══════════════════════════════════════

    cur.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (
        session['user_id'],
    ))

    user = cur.fetchone()

    # ═══════════════════════════════════════
    # TOTAL FARMERS
    # ═══════════════════════════════════════

    cur.execute("""
        SELECT COUNT(*) AS total_farmers
        FROM users
    """)

    farmers_data = cur.fetchone()

    total_farmers = farmers_data['total_farmers']

    # ═══════════════════════════════════════
    # TOTAL GROUPS
    # ═══════════════════════════════════════

    cur.execute("""
        SELECT COUNT(*) AS total_groups
        FROM communities
    """)

    groups_data = cur.fetchone()

    total_groups = groups_data['total_groups']

    # ═══════════════════════════════════════
    # TOTAL DISCUSSIONS
    # ═══════════════════════════════════════

    cur.execute("""
        SELECT COUNT(*) AS total_discussions
        FROM community_messages
    """)

    discussions_data = cur.fetchone()

    total_discussions = discussions_data['total_discussions']

    # ═══════════════════════════════════════
    # FORMAT COUNTS
    # ═══════════════════════════════════════

    def format_count(num):

        if num >= 1000000:
            return f"{num / 1000000:.1f}M"

        elif num >= 1000:
            return f"{num / 1000:.1f}K"

        else:
            return str(num)

    total_farmers = format_count(total_farmers)
    total_groups = format_count(total_groups)
    total_discussions = format_count(total_discussions)

    # CLOSE CURSOR
    cur.close()

    # RENDER PAGE
    return render_template(
        'community.html',

        communities=communities,
        user=user,

        total_farmers=total_farmers,
        total_groups=total_groups,
        total_discussions=total_discussions
    )

# =====================================================
# CREATE COMMUNITY
# =====================================================

@app.route('/create_community', methods=['POST'])
def create_community():

    # =============================
    # LOGIN CHECK
    # =============================

    if 'user_id' not in session:

        flash("Please login first", "warning")

        return redirect(url_for('login'))

    # =============================
    # FORM DATA
    # =============================

    community_name = request.form['community_name']

    description = request.form['description']

    community_image = request.files['community_image']

    filename = ""

    # =============================
    # SAVE IMAGE
    # =============================

    if community_image and community_image.filename != "":

        filename = secure_filename(
            community_image.filename
        )

        image_path = os.path.join(
            app.config['COMMUNITY_UPLOAD_FOLDER'],
            filename
        )

        community_image.save(image_path)

    # =============================
    # INSERT INTO DATABASE
    # =============================

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO communities
        (
            community_name,
            description,
            community_image,
            created_by
        )
        VALUES (%s,%s,%s,%s)
    """, (

        community_name,
        description,
        filename,
        session['user_id']

    ))

    mysql.connection.commit()

    cur.close()

    flash(
        "Community Created Successfully",
        "success"
    )

    return redirect(url_for('community'))
   
@app.route('/join_community/<int:community_id>', methods=['POST'])
def join_community(community_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT *
    FROM community_members
    WHERE community_id=%s
    AND user_id=%s
    """, (
        community_id,
        session['user_id']
    ))

    member = cur.fetchone()

    if not member:

        cur.execute("""
        INSERT INTO community_members
        (community_id,user_id)
        VALUES(%s,%s)
        """, (
            community_id,
            session['user_id']
        ))

        mysql.connection.commit()

    cur.close()

    flash("Joined Community Successfully", "success")

    return redirect(url_for('community'))
@app.route('/delete_community/<int:community_id>')
def delete_community(community_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
    DELETE FROM communities
    WHERE id=%s
    AND created_by=%s
    """, (
        community_id,
        session['user_id']
    ))

    mysql.connection.commit()

    cur.close()

    flash("Community Deleted", "success")

    return redirect(url_for('community'))
@app.route('/community_chat/<int:community_id>')
def community_chat(community_id):

    # ================= LOGIN CHECK =================

    if 'user_id' not in session:
        return redirect(url_for('login'))

    # ================= CURSOR =================

    cur = mysql.connection.cursor()

    # IMPORTANT:
    # Dictionary cursor use chesthunam
    # app.py top lo import cheyyi:
    #
    # from MySQLdb.cursors import DictCursor
    #
    # then below line use cheyyi

    cur = mysql.connection.cursor(DictCursor)

    # ================= COMMUNITY DETAILS =================

    cur.execute("""

        SELECT *
        FROM communities
        WHERE id = %s

    """, (community_id,))

    community = cur.fetchone()

    # ================= CURRENT USER =================

    cur.execute("""

        SELECT *
        FROM users
        WHERE id = %s

    """, (session['user_id'],))

    user = cur.fetchone()

    # ================= COMMUNITY MESSAGES =================

    cur.execute("""

        SELECT
            community_messages.*,
            users.username,
            users.profile_image

        FROM community_messages

        JOIN users
        ON community_messages.user_id = users.id

        WHERE community_messages.community_id = %s

        ORDER BY community_messages.id ASC

    """, (community_id,))

    messages = cur.fetchall()

    # ================= CLOSE CURSOR =================

    cur.close()

    # ================= RENDER TEMPLATE =================

    return render_template(

        'community_chat.html',

        community=community,

        messages=messages,

        user=user

    )
# =====================================================
# SEND COMMUNITY MESSAGE
# =====================================================

@app.route('/send_community_message/<int:community_id>', methods=['POST'])
def send_community_message(community_id):

    # ================= LOGIN CHECK =================

    if 'user_id' not in session:
        return redirect(url_for('login'))

    import os
    import time

    from werkzeug.utils import secure_filename

    # ================= FORM DATA =================

    message = request.form.get('message', '').strip()

    image = request.files.get('image')

    video = request.files.get('video')

    document = request.files.get('document')

    # ================= FILE VARIABLES =================

    image_name = None
    video_name = None
    document_name = None

    # ================= UPLOAD FOLDER =================

    upload_folder = app.config['COMMUNITY_FILES_UPLOAD_FOLDER']

    # AUTO CREATE FOLDER

    os.makedirs(upload_folder, exist_ok=True)

    # =====================================================
    # IMAGE UPLOAD
    # =====================================================

    if image and image.filename != '':

        image_name = (
            str(int(time.time())) +
            "_" +
            secure_filename(image.filename)
        )

        image.save(
            os.path.join(
                upload_folder,
                image_name
            )
        )

        print("IMAGE SAVED :", image_name)

    # =====================================================
    # VIDEO UPLOAD
    # =====================================================

    if video and video.filename != '':

        video_name = (
            str(int(time.time())) +
            "_" +
            secure_filename(video.filename)
        )

        video.save(
            os.path.join(
                upload_folder,
                video_name
            )
        )

        print("VIDEO SAVED :", video_name)

    # =====================================================
    # DOCUMENT UPLOAD
    # =====================================================

    if document and document.filename != '':

        document_name = (
            str(int(time.time())) +
            "_" +
            secure_filename(document.filename)
        )

        document.save(
            os.path.join(
                upload_folder,
                document_name
            )
        )

        print("DOCUMENT SAVED :", document_name)

    # =====================================================
    # SAVE TO DATABASE
    # =====================================================

    cur = mysql.connection.cursor()

    cur.execute("""

        INSERT INTO community_messages
        (

            community_id,
            user_id,
            message,
            image,
            video,
            document

        )

        VALUES(%s,%s,%s,%s,%s,%s)

    """, (

        community_id,
        session['user_id'],
        message,
        image_name,
        video_name,
        document_name

    ))

    mysql.connection.commit()

    cur.close()

    return redirect(
        url_for(
            'community_chat',
            community_id=community_id
        )
    )
# =====================================================
# COMMUNITY MEMBERS PAGE
# =====================================================

@app.route('/community_members/<int:community_id>')
def community_members(community_id):

    # ==========================
    # LOGIN CHECK
    # ==========================
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ==========================
    # COMMUNITY DETAILS
    # ==========================
    cur.execute("""
        SELECT
            c.*,
            u.username
        FROM communities c
        JOIN users u
        ON c.created_by = u.id
        WHERE c.id = %s
    """, (community_id,))

    community = cur.fetchone()

    # ==========================
    # COMMUNITY MEMBERS
    # ==========================
    cur.execute("""
        SELECT
            u.id,
            u.username,
            u.profile_image
        FROM community_members cm
        JOIN users u
        ON cm.user_id = u.id
        WHERE cm.community_id = %s
        ORDER BY u.username ASC
    """, (community_id,))

    members = cur.fetchall()

    # ==========================
    # MEMBER COUNT
    # ==========================
    cur.execute("""
        SELECT COUNT(*) AS total_members
        FROM community_members
        WHERE community_id = %s
    """, (community_id,))

    member_count = cur.fetchone()['total_members']

    cur.close()

    # ==========================
    # SEND TO TEMPLATE
    # ==========================
    return render_template(
        'view_community_profilemembers.html',
        community=community,
        members=members,
        member_count=member_count,
        current_user=session['user_id']
    )
@app.route('/remove_member/<int:community_id>/<int:user_id>', methods=['POST'])
def remove_member(community_id, user_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Community owner check
    cur.execute("""
        SELECT created_by
        FROM communities
        WHERE id=%s
    """, (community_id,))

    community = cur.fetchone()

    if not community:
        flash("Community not found", "danger")
        return redirect(url_for('community'))

    # Only owner can remove
    if community['created_by'] != session['user_id']:
        flash("Access denied", "danger")
        return redirect(url_for('community'))

    cur.execute("""
        DELETE FROM community_members
        WHERE community_id=%s
        AND user_id=%s
    """, (community_id, user_id))

    mysql.connection.commit()

    cur.close()

    flash("Member removed successfully", "success")

    return redirect(
        url_for(
            'community_members',
            community_id=community_id
        )
    )
@app.route('/leave_community/<int:community_id>', methods=['POST'])
def leave_community(community_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        DELETE FROM community_members
        WHERE community_id=%s
        AND user_id=%s
    """, (community_id, session['user_id']))

    mysql.connection.commit()

    cur.close()

    flash("You left the community", "success")

    return redirect(url_for('community'))

@app.route('/upload_community_file/<int:community_id>', methods=['POST'])
def upload_community_file(community_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    file = request.files['file']

    if file and file.filename:

        filename = secure_filename(file.filename)

        file.save(
            os.path.join(
                app.config['COMMUNITY_UPLOAD_FOLDER'],
                filename
            )
        )

        extension = filename.split('.')[-1].lower()

        if extension in ['jpg','jpeg','png','gif','webp']:
            file_type = 'image'

        elif extension in ['mp4','mov','avi','mkv']:
            file_type = 'video'

        else:
            file_type = 'document'

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO community_files
            (
                community_id,
                user_id,
                file_name,
                file_type
            )
            VALUES(%s,%s,%s,%s)
        """,(
            community_id,
            session['user_id'],
            filename,
            file_type
        ))

        mysql.connection.commit()

        cur.close()

    return redirect(
        url_for(
            'community_chat',
            community_id=community_id
        )
    )
@app.route('/create_poll/<int:community_id>', methods=['POST'])
def create_poll(community_id):

    question = request.form['question']

    options = request.form.getlist('options[]')

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO community_polls
        (
            community_id,
            user_id,
            question
        )
        VALUES(%s,%s,%s)
    """,(
        community_id,
        session['user_id'],
        question
    ))

    poll_id = cur.lastrowid

    for option in options:

        if option.strip():

            cur.execute("""
                INSERT INTO community_poll_options
                (
                    poll_id,
                    option_text
                )
                VALUES(%s,%s)
            """,(
                poll_id,
                option
            ))

    mysql.connection.commit()

    cur.close()

    return redirect(
        url_for(
            'community_chat',
            community_id=community_id
        )
    )
@app.route('/vote_poll/<int:poll_id>', methods=['POST'])
def vote_poll(poll_id):

    option_id = request.form['option_id']

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO community_poll_votes
        (
            poll_id,
            option_id,
            user_id
        )
        VALUES(%s,%s,%s)
    """,(
        poll_id,
        option_id,
        session['user_id']
    ))

    mysql.connection.commit()

    cur.close()

    return redirect(request.referrer)
@app.route('/analytics')
def analytics():

    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Logged User
    cur.execute(
        "SELECT * FROM users WHERE id=%s",
        (session['user_id'],)
    )
    user = cur.fetchone()

    # =================================
    # TOTAL COUNTS
    # =================================

    cur.execute("SELECT COUNT(*) total FROM posts")
    total_posts = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) total FROM marketplace_items")
    total_marketplace = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) total FROM jobs")
    total_jobs = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) total FROM communities")
    total_community = cur.fetchone()['total']

    # =================================
    # MARKETPLACE CATEGORY COUNTS
    # =================================

    crop_count = 0
    seed_count = 0
    fertilizer_count = 0
    tool_count = 0
    machinery_count = 0
    organic_count = 0

    cur.execute("""
        SELECT category, COUNT(*) total
        FROM marketplace_items
        GROUP BY category
    """)

    categories = cur.fetchall()

    for row in categories:

        category = str(row['category']).strip().lower()

        if 'crop' in category:
            crop_count = row['total']

        elif 'seed' in category:
            seed_count = row['total']

        elif 'fertilizer' in category:
            fertilizer_count = row['total']

        elif 'tool' in category:
            tool_count = row['total']

        elif 'machinery' in category:
            machinery_count = row['total']

        elif 'organic' in category:
            organic_count = row['total']

    # =================================
    # JOB TYPE COUNTS
    # =================================

    full_time_jobs = 0
    part_time_jobs = 0
    internship_jobs = 0
    contract_jobs = 0

    cur.execute("""
        SELECT job_type, COUNT(*) total
        FROM jobs
        GROUP BY job_type
    """)

    job_types = cur.fetchall()

    for row in job_types:

        job_type = str(row['job_type']).strip().lower()

        if 'full' in job_type:
            full_time_jobs = row['total']

        elif 'part' in job_type:
            part_time_jobs = row['total']

        elif 'intern' in job_type:
            internship_jobs = row['total']

        elif 'contract' in job_type:
            contract_jobs = row['total']

    cur.close()

    return render_template(
        'analytics.html',

        user=user,

        total_posts=total_posts,
        total_marketplace=total_marketplace,
        total_jobs=total_jobs,
        total_community=total_community,

        crop_count=crop_count,
        seed_count=seed_count,
        fertilizer_count=fertilizer_count,
        tool_count=tool_count,
        machinery_count=machinery_count,
        organic_count=organic_count,

        full_time_jobs=full_time_jobs,
        part_time_jobs=part_time_jobs,
        internship_jobs=internship_jobs,
        contract_jobs=contract_jobs
    )
# =====================================================
# SETTINGS PAGE
# =====================================================

@app.route('/settings')
def settings():

    # ==============================
    # CHECK LOGIN
    # ==============================

    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # ==============================
    # DICT CURSOR
    # ==============================

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ==============================
    # FETCH LOGGED IN USER
    # ==============================

    cur.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (session['user_id'],))

    user = cur.fetchone()

    # ==============================
    # CLOSE CURSOR
    # ==============================

    cur.close()

    # ==============================
    # RENDER TEMPLATE
    # ==============================

    return render_template(
        'settings.html',
        user=user
    )
# =====================================================
# CHANGE LANGUAGE
# =====================================================
@app.route('/update_language', methods=['POST'])
def update_language():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    language = request.form.get('language')

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE users
        SET language=%s
        WHERE id=%s
    """, (
        language,
        session['user_id']
    ))

    mysql.connection.commit()
    cur.close()

    flash("Language updated successfully!", "success")

    return redirect(url_for('settings'))


# ============================================
# UPDATE NOTIFICATIONS
# ============================================

@app.route('/update_notifications', methods=['POST'])
def update_notifications():

    # LOGIN CHECK
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # GET VALUE
    notifications = request.form.get('notifications')

    # MYSQL CURSOR
    cur = mysql.connection.cursor()

    # UPDATE DATABASE
    cur.execute("""
        UPDATE users
        SET notifications = %s
        WHERE id = %s
    """, (
        notifications,
        session['user_id']
    ))

    mysql.connection.commit()

    cur.close()

    flash("Notification settings updated successfully!", "success")

    return redirect(url_for('settings'))
# =====================================================
# ADMIN DASHBOARD
# =====================================================
@app.route('/admin_dashboard')
def admin_dashboard():

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ==========================
    # TOTAL USERS
    # ==========================
    cur.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cur.fetchone()['total']

    # ==========================
    # TOTAL POSTS
    # ==========================
    cur.execute("SELECT COUNT(*) AS total FROM posts")
    total_posts = cur.fetchone()['total']

    # ==========================
    # MARKETPLACE COUNT
    # Mee database lo marketplace table lekapothe
    # actual table name pettali
    # ==========================

    try:
        cur.execute("SELECT COUNT(*) AS total FROM marketplace")
        total_marketplace = cur.fetchone()['total']
    except:
        total_marketplace = 0

    # ==========================
    # JOBS COUNT
    # jobs table lekapothe error rakunda
    # ==========================

    try:
        cur.execute("SELECT COUNT(*) AS total FROM jobs")
        total_jobs = cur.fetchone()['total']
    except:
        total_jobs = 0

    # ==========================
    # RECENT USERS
    # ==========================

    cur.execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
        LIMIT 20
    """)
    users = cur.fetchall()

    # ==========================
    # USER REGISTRATION CHART
    # created_at column unte
    # ==========================

    try:
        cur.execute("""
            SELECT
            MONTHNAME(created_at) AS month,
            COUNT(*) AS total
            FROM users
            GROUP BY MONTH(created_at)
            ORDER BY MONTH(created_at)
        """)

        months = cur.fetchall()

        month_labels = [row['month'] for row in months]
        month_counts = [row['total'] for row in months]

    except:
        month_labels = []
        month_counts = []

    # ==========================
    # PROFESSION CHART
    # ==========================

    try:
        cur.execute("""
            SELECT profession,
                   COUNT(*) AS total
            FROM users
            GROUP BY profession
        """)

        professions = cur.fetchall()

        profession_labels = [row['profession'] for row in professions]
        profession_counts = [row['total'] for row in professions]

    except:
        profession_labels = []
        profession_counts = []

    cur.close()

    return render_template(
        'admin_dashboard.html',

        users=users,

        total_users=total_users,
        total_posts=total_posts,
        total_marketplace=total_marketplace,
        total_jobs=total_jobs,

        month_labels=month_labels,
        month_counts=month_counts,

        profession_labels=profession_labels,
        profession_counts=profession_counts
    )
# =====================================================
# SOCKET IO CHAT (FIXED)
# =====================================================

# =====================================================
# SOCKET IO CHAT (FIXED)
# =====================================================

from flask_socketio import emit, join_room

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    print("Joined room:", room)


@socketio.on('send_message')
def handle_send_message(data):

    room = data['room']
    message = data['message']
    sender_id = data['sender_id']

    print("Message:", message)

    emit('message', {
        'message': message,
        'sender_id': sender_id
    }, room=room)

# =========================================================
# ADD GOVT SCHEME PAGE (DISPLAY PAGE)
# =========================================================

@app.route('/add_govt_schemes')
def add_govt_schemes():

    cursor = mysql.connection.cursor()   # ✅ FIXED

    cursor.execute("SELECT * FROM govt_schemes")
    schemes = cursor.fetchall()

    cursor.close()

    return render_template('add_govt_schemes.html', schemes=schemes)

# =========================================================
# INSERT SCHEME
# =========================================================

@app.route('/insert_scheme', methods=['POST'])
def insert_scheme():

    scheme_name = request.form.get('scheme_name')
    category = request.form.get('category')
    description = request.form.get('description')
    eligibility = request.form.get('eligibility')
    benefits = request.form.get('benefits')
    state = request.form.get('state')
    website_link = request.form.get('website_link')
    image_url = request.form.get('image_url')

    cursor = mysql.connection.cursor()

    sql = """
        INSERT INTO govt_schemes
        (
            scheme_name,
            category,
            description,
            eligibility,
            benefit,
            state,
            website_link,
            image_url
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        scheme_name,
        category,
        description,
        eligibility,
        benefits,
        state,
        website_link,
        image_url
    )

    cursor.execute(sql, values)
    mysql.connection.commit()
    cursor.close()

    flash('Government Scheme Added Successfully!', 'success')

    return redirect(url_for('add_govt_schemes'))


# =========================================================
# EDIT SCHEME PAGE
# =========================================================

@app.route("/edit_scheme/<int:id>", methods=["GET"])
def edit_scheme(id):

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM govt_schemes WHERE id=%s", (id,))
    scheme = cursor.fetchone()
    cursor.close()

    return render_template("edit_govt_scheme.html", scheme=scheme)


# =========================================================
# UPDATE SCHEME
# =========================================================

@app.route("/update_scheme/<int:id>", methods=["POST"])
def update_scheme(id):

    scheme_name = request.form.get("scheme_name")
    category = request.form.get("category")
    description = request.form.get("description")
    eligibility = request.form.get("eligibility")
    benefits = request.form.get("benefits")
    state = request.form.get("state")
    website_link = request.form.get("website_link")
    image_url = request.form.get("image_url")

    cursor = mysql.connection.cursor()

    sql = """
        UPDATE govt_schemes SET
            scheme_name=%s,
            category=%s,
            description=%s,
            eligibility=%s,
            benefit=%s,
            state=%s,
            website_link=%s,
            image_url=%s
        WHERE id=%s
    """

    values = (
        scheme_name,
        category,
        description,
        eligibility,
        benefits,
        state,
        website_link,
        image_url,
        id
    )

    cursor.execute(sql, values)
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for("add_govt_schemes"))


# =========================================================
# DELETE SCHEME
# =========================================================

@app.route("/delete_scheme/<int:id>")
def delete_scheme(id):

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM govt_schemes WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for("add_govt_schemes"))
@app.route('/network')
def network():

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM users")

    users = cur.fetchall()

    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))

    user = cur.fetchone()

    cur.close()

    return render_template(
        'network.html',
        users=users,
        user=user
    )
# =========================================================
# TODAY MARKET LIVE RATES
# =========================================================
@app.route('/view_today_marketrate')
def view_today_marketrate():

    import requests

    agriculture_rates = []

    try:

        API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

        response = requests.get(
            url,
            params={
                "api-key": API_KEY,
                "format": "json",
                "limit": 10
            },
            timeout=20
        )

        print("STATUS:", response.status_code)

        if response.status_code == 200:

            data = response.json()

            records = data.get("records", [])

            print("TOTAL RECORDS:", len(records))

            for item in records:

                agriculture_rates.append({

                    "crop": item.get("commodity", "N/A"),

                    "market": item.get("market", "N/A"),

                    "price": item.get("modal_price", "0"),

                    "unit": "Per Quintal",

                    "icon": "🌾"

                })

        else:

            print("API ERROR:", response.text)

    except Exception as e:

        print("MARKET API ERROR:", e)

    return render_template(
        "view_today_marketrate.html",
        agriculture_rates=agriculture_rates
    )

# =====================================================
# RUN APP
# =====================================================

if __name__ == '__main__':

    socketio.run(app, debug=True)

