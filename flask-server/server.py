from tensorflow.keras.models import load_model
import numpy as np
from PIL import Image
from tensorflow.keras.preprocessing import image
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from joblib import load
import cv2

import moviepy.editor as mp
import librosa


def preprocess_video(video_path):
    video = mp.VideoFileClip(video_path)
    if video.audio is None:
        raise ValueError(f"No audio in video: {video_path}")
    audio = video.audio.to_soundarray()
    mfccs = librosa.feature.mfcc(y=audio[:, 0], sr=audio.shape[0], n_mfcc=13)
    avg_mfccs = np.mean(mfccs, axis=1)
    return avg_mfccs

# Importing deps for image prediction


app = Flask(__name__)
CORS(app, resources={
     r"/*": {"origins": "http://localhost:3000"}})


@app.route("/")
def home():
    return {"message": "Test Backend Server"}


@app.route("/upload_video", methods=['POST'])
def upload_video():
    print(request.files)
    print(request.form)
    video_path = None

    if 'file' not in request.files:
        print('No file part.')
        # Handle the case for sample video
        if 'filepath' in request.form:
            video_path = f"./static/{request.form['filepath'].split('/')[-1]}"
        else:
            return jsonify({"error": "No video part in the request."}), 400
    else:
        file = request.files['file']
        if file.filename == '':
            print('No video selected.')
            return jsonify({"error": "No video selected."}), 400

        try:
            file.save('uploads/' + file.filename)
            video_path = f"./uploads/{file.filename}"
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500

    if video_path:
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frames_to_extract = np.random.choice(
                total_frames, min(250, total_frames), replace=False)  # Extract 250 random frames

            ai_count = 0
            human_count = 0
            loaded_model = load_model('./model/cnn_model2.h5')
            image_score = 0

            for frame_no in frames_to_extract:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                ret, frame = cap.read()
                if ret:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    img = img.resize((224, 224))
                    x = image.img_to_array(img)
                    x = np.expand_dims(x, axis=0)
                    x /= 255

                    prediction = loaded_model.predict(x)
                    image_score += prediction
                    if prediction < 0.5:
                        human_count += 1
                    else:
                        ai_count += 1
            image_score = image_score / len(frames_to_extract)
            loaded_model = load('./model/audio.pkl')
            features = preprocess_video(video_path)
            prediction = loaded_model.predict([features])
            print("Image Score: ", image_score)
            print("Audio Score: ", prediction)

            if 'filepath' not in request.form and os.path.exists(video_path):
                os.remove(video_path)

            majority_vote = "AI Generated" if ai_count > human_count else "Human Generated"
            if majority_vote == "AI Generated" or prediction < 0.5:
                return jsonify({"message": "AI Generated"})
            else:
                return jsonify({"message": "Human Generated"})

        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Unexpected error occurred."}), 500


@app.route("/upload_audio", methods=['POST'])
def upload_audio():
    print(request.files)
    print(request.form)
    video_path = None

    if 'file' not in request.files:
        print('No file part.')
        # Handle the case for sample video
        if 'filepath' in request.form:
            video_path = f"./static/{request.form['filepath'].split('/')[-1]}"
        else:
            return jsonify({"error": "No file part in the request."}), 400
    else:
        file = request.files['file']
        if file.filename == '':
            print('No file selected.')
            return jsonify({"error": "No file selected."}), 400

        try:
            file.save('uploads/' + file.filename)
            video_path = f"./uploads/{file.filename}"
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500

    if video_path:
        try:
            loaded_model = load('./model/audio.pkl')
            features = preprocess_video(video_path)
            prediction = loaded_model.predict([features])

            if 'filepath' not in request.form and os.path.exists(video_path):
                os.remove(video_path)
            print(prediction)

            if prediction >= 0.5:
                return jsonify({"message": "Human Generated"})
            else:
                return jsonify({"message": "AI Generated"})
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Unexpected error occurred."}), 500


@app.route("/upload", methods=['POST'])
def upload():
    print(request.files)
    print(request.form)
    img_path = None

    if 'file' not in request.files:
        print('No file part.')
        # Handle the case for sample image
        if 'filepath' in request.form:
            img_path = f"./static/{request.form['filepath'].split('/')[-1]}"
        else:
            return jsonify({"error": "No file part in the request."}), 400
    else:
        file = request.files['file']
        if file.filename == '':
            print('No file selected.')
            return jsonify({"error": "No file selected."}), 400

        try:
            file.save('uploads/' + file.filename)
            img_path = f"./uploads/{file.filename}"
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500

    if img_path:
        try:
            # Load the image to predict
            img = image.load_img(img_path, target_size=(224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x /= 255

            loaded_model = load_model('./model/cnn_model2.h5')

            # Make the prediction
            prediction = loaded_model.predict(x)
            if 'filepath' not in request.form and os.path.exists(f"./uploads/{file.filename}"):
                os.remove(f"uploads/{file.filename}")
            print(prediction)
            if prediction < 0.5:
                return jsonify({"message": "Human Generated"})
            else:
                return jsonify({"message": "AI Generated"})
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Unexpected error occurred."}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
