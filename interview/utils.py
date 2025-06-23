import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime

mp_hands = mp.solutions.hands
mp_face_detection = mp.solutions.face_detection
finger_tips = [
    mp_hands.HandLandmark.THUMB_TIP,
    mp_hands.HandLandmark.INDEX_FINGER_TIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
    mp_hands.HandLandmark.RING_FINGER_TIP,
    mp_hands.HandLandmark.PINKY_TIP
]

action_logs = []

def log_action(action_data):
    action_logs.append(action_data)

def compress_actions(actions_list, min_duration=2):
    def parse_time(timestr):
        return datetime.strptime(timestr, "%M:%S")

    grouped_data = {}
    for data in actions_list:
        time = data.get("time")
        action = data.get("action")
        if time not in grouped_data:
            grouped_data[time] = []
        grouped_data[time].append(action)

    compressed_data = []
    prev_time = None
    prev_actions = None
    start_time = None

    for time in sorted(grouped_data.keys()):
        actions = grouped_data[time]
        actions_tuple = tuple(sorted(actions))
        current_dt = parse_time(time)

        if prev_time is not None:
            prev_dt = parse_time(prev_time)
            time_gap = (current_dt - prev_dt).total_seconds()

            if time_gap != 1 or actions_tuple != prev_actions:
                duration = (parse_time(prev_time) - parse_time(start_time)).total_seconds() + 1
                if duration >= min_duration:
                    compressed_data.append({
                        "start": start_time,
                        "end": prev_time,
                        "actions": list(set(prev_actions))
                    })
                elif "hand moving" in prev_actions:
                    compressed_data.append({
                        "start": start_time,
                        "end": prev_time,
                        "actions": "hand moving"
                    })

                start_time = time
        else:
            start_time = time

        prev_time = time
        prev_actions = actions_tuple

    if prev_actions is not None:
        duration = (parse_time(prev_time) - parse_time(start_time)).total_seconds() + 1
        if duration >= min_duration:
            compressed_data.append({
                "start": start_time,
                "end": prev_time,
                "actions": list(set(prev_actions))
            })

    return compressed_data

class HandMovementDetector:
    def __init__(self, sensitivity=0.5):
        self.hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)
        self.prev_finger_positions = [None, None]
        self.sensitivity = sensitivity
        self.small_threshold = 5 * sensitivity
        self.logged_times_movement = set()
        self.logged_times_near_head = set()

    def detect_hand_movement(self, hand_landmarks, w, h, hand_index):
        if hand_index >= len(self.prev_finger_positions):
            self.prev_finger_positions.extend([None] * (hand_index - len(self.prev_finger_positions) + 1))

        hand_positions = [
            np.array([int(hand_landmarks.landmark[tip].x * w),
                      int(hand_landmarks.landmark[tip].y * h)])
            for tip in finger_tips
        ]

        movement_label = "stop"
        if self.prev_finger_positions[hand_index] is not None:
            distances = [
                np.linalg.norm(curr - prev)
                for curr, prev in zip(hand_positions, self.prev_finger_positions[hand_index])
            ]
            avg_movement = np.mean(distances)
            if avg_movement > self.small_threshold:
                movement_label = "moving"

        self.prev_finger_positions[hand_index] = hand_positions
        return movement_label

    def process_frame(self, frame, cap):
        h, w, _ = frame.shape
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results_hands = self.hands.process(image_rgb)
        results_faces = self.face_detection.process(image_rgb)
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

        movement_detected = False
        if results_hands.multi_hand_landmarks:
            for hand_index, hand_landmarks in enumerate(results_hands.multi_hand_landmarks):
                movement_label = self.detect_hand_movement(hand_landmarks, w, h, hand_index)
                if movement_label == "moving":
                    movement_detected = True

        if movement_detected:
            total_seconds = int(timestamp_ms // 1000)
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            if time_str not in self.logged_times_movement:
                self.logged_times_movement.add(time_str)
                action_data = {"time": time_str, "action": "손의 불필요한 움직임이 감지되었습니다"}
                log_action(action_data)

        if results_faces.detections and results_hands.multi_hand_landmarks:
            face = results_faces.detections[0]
            bboxC = face.location_data.relative_bounding_box
            face_bbox = [int(bboxC.xmin * w), int(bboxC.ymin * h),
                         int(bboxC.width * w), int(bboxC.height * h)]
            padding = 20
            padding_top = 80
            expanded_bbox = [
                face_bbox[0] - padding,
                face_bbox[1] - padding_top,
                face_bbox[2] + 2 * padding,
                face_bbox[3] + 2 * padding + padding_top
            ]

            for hand_landmarks in results_hands.multi_hand_landmarks:
                hand_positions = [
                    np.array([int(hand_landmarks.landmark[tip].x * w),
                              int(hand_landmarks.landmark[tip].y * h)])
                    for tip in finger_tips
                ]
                for pos in hand_positions:
                    x, y = pos
                    if (expanded_bbox[0] <= x <= expanded_bbox[0] + expanded_bbox[2] and
                            expanded_bbox[1] <= y <= expanded_bbox[1] + expanded_bbox[3]):
                        total_seconds = int(timestamp_ms // 1000)
                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        if time_str not in self.logged_times_near_head:
                            self.logged_times_near_head.add(time_str)
                            action_data = {"time": time_str, "action": "손이 얼굴 주변에 위치해 면접에 방해가 될 수 있습니다"}
                            log_action(action_data)
                        break

        return frame

class UpperBodyPostureDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.tilt_threshold = 4
        self.logged_times = set()

    def calculate_slope(self, point1, point2):
        delta_x = point2[0] - point1[0]
        delta_y = point2[1] - point1[1]
        return np.arctan2(delta_y, delta_x) * 180 / np.pi

    def process_frame(self, frame, cap):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        output_frame = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = frame.shape

            left_shoulder = (
                int((1 - landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x) * w),
                int(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y * h)
            )
            right_shoulder = (
                int((1 - landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x) * w),
                int(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h)
            )

            shoulder_slope = self.calculate_slope(left_shoulder, right_shoulder)
            shoulder_tilted = abs(shoulder_slope) > self.tilt_threshold

            if shoulder_tilted:
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                total_seconds = int(timestamp_ms // 1000)
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                if time_str not in self.logged_times:
                    self.logged_times.add(time_str)
                    action_data = {"time": time_str, "action": "어깨가 기울어져 있어 자세가 불안정해 보일 수 있습니다"}
                    log_action(action_data)

        return output_frame

class EyeTrackingDetector:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
        self.left_eye_idx = [33, 133]       # 왼쪽 눈 좌우
        self.right_eye_idx = [362, 263]     # 오른쪽 눈 좌우
        self.left_iris_idx = [468]          # 왼쪽 홍채 중심
        self.right_iris_idx = [473]         # 오른쪽 홍채 중심
        self.logged_times = set()

    def get_eye_direction(self, eye_corner1, eye_corner2, iris_center):
        eye_width = eye_corner2[0] - eye_corner1[0]
        iris_pos = iris_center[0] - eye_corner1[0]
        ratio = iris_pos / eye_width if eye_width != 0 else 0.5

        if ratio < 0.44: #right
            return "시선이 산만하여 눈을 마주치지 않는 것으로 보입니다"
        elif ratio > 0.56: #left
            return "시선이 산만하여 눈을 마주치지 않는 것으로 보입니다"
        else:
            return "center"

    def process_frame(self, frame, cap):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_eye = [face_landmarks.landmark[i] for i in self.left_eye_idx]
                right_eye = [face_landmarks.landmark[i] for i in self.right_eye_idx]
                left_iris = face_landmarks.landmark[self.left_iris_idx[0]]
                right_iris = face_landmarks.landmark[self.right_iris_idx[0]]

                l_eye_pts = [(int(p.x * w), int(p.y * h)) for p in left_eye]
                r_eye_pts = [(int(p.x * w), int(p.y * h)) for p in right_eye]
                l_iris_pt = (int(left_iris.x * w), int(left_iris.y * h))
                r_iris_pt = (int(right_iris.x * w), int(right_iris.y * h))

                left_direction = self.get_eye_direction(l_eye_pts[0], l_eye_pts[1], l_iris_pt)
                right_direction = self.get_eye_direction(r_eye_pts[0], r_eye_pts[1], r_iris_pt)

                if left_direction == right_direction and left_direction != "center":
                    timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                    total_seconds = int(timestamp_ms // 1000)
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    if time_str not in self.logged_times:
                        self.logged_times.add(time_str)
                        action_data = {"time": time_str, "action": left_direction}
                        log_action(action_data)
        return frame

def analyze_behavior(video_path):
    cap = cv2.VideoCapture(video_path)

    type1 = HandMovementDetector()
    type2 = UpperBodyPostureDetector()
    type3 = EyeTrackingDetector()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = type1.process_frame(frame, cap)
        frame = type2.process_frame(frame, cap)
        frame = type3.process_frame(frame, cap)

    cap.release()
    return compress_actions(action_logs)