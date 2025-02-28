import cv2
import mediapipe as mp
import logging

# 사용자 행동 분석
def analyze_behavior(video_path):
    try:
        mp_holistic=mp.solutions.holistic
        holistic=mp_holistic.Holistic()
        cap=cv2.VideoCapture(video_path)

        fps=int(cap.get(cv2.CAP_PROP_FPS))
        frame_idx=0
        behavior_events=[]

        current_event=None
        event_start_time=None

        while cap.isOpened():
            ret, frame=cap.read()
            if not ret:
                break

            frame_rgb=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results=holistic.process(frame_rgb)

            detected_behavior=None

            #시선 방향 감지
            if results.face_landmarks:
                nose_tip=results.face_landmarks.landmark[1]
                if nose_tip.x < 0.4:
                    detected_behavior="왼쪽을 봄"
                elif nose_tip.x > 0.6:
                    detected_behavior="오른쪽을 봄"

            #손 사용 감지
            if results.left_hand_landmarks:
                detected_behavior="왼손 사용"
            if results.right_hand_landmarks:
                detected_behavior="오른손 사용"

            #행동 지속 시간
            if detected_behavior:
                if current_event==detected_behavior:
                    event_end_time=round(frame_idx/fps,2)
                else:
                    if current_event:
                        behavior_events.append({
                            "event":current_event,
                            "start_time":round(event_start_time,2),
                            "end_time":round(event_end_time,2)
                        })
                    current_event=detected_behavior
                    event_start_time=round(frame_idx/fps,2)
                    event_end_time=event_start_time

            frame_idx+=1

        if current_event:
            behavior_events.append({
                "event":current_event,
                "start_time":round(event_start_time,2),
                "end_time":round(event_end_time,2)
            })

        cap.release()
        holistic.close()

        return {"detected_behaviors":behavior_events}

    except Exception as e:
        logging.error(f"행동 분석 중 오류 발생:{e}")
        return None