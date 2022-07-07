import torch,cv2,dlib,time,datetime,os
import numpy as np
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject
from threading import Thread
import requests
import sys
import platform

def non_max_suppression_fast(boxes, overlapThresh):
    try:
        if len(boxes) == 0:
            return []
        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        pick = []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(y2)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[:last]]

            idxs = np.delete(idxs, np.concatenate(([last],
                                                   np.where(overlap > overlapThresh)[0])))

        return boxes[pick].astype("int")
    except Exception as e:
        print("Exception occurred in non_max_suppression : {}".format(e))

def create_folder():
    base_dir = os.path.dirname(os.path.abspath('__file__'))
    backup_vdo = os.path.join(base_dir, "backup_video")
    backup_img = os.path.join(base_dir, "backup_img")
    date_img = os.path.join(backup_img, "{}".format(datetime.date.today()))
    date_vdo = os.path.join(backup_vdo, "{}".format(datetime.date.today()))

    if os.path.isdir(backup_img) == False:
        os.mkdir(backup_img)
    if os.path.isdir(date_img) == False:
        os.mkdir(date_img)
    if os.path.isdir(backup_vdo) == False:
        os.mkdir(backup_vdo)
    if os.path.isdir(date_vdo) == False:
        os.mkdir(date_vdo)

def request_post(person_in,person_pass,device,url = 'https://mltest.advice.co.th/mltest/count_post.php'):
    # data = {"data": file}
    # text = {"Username": nameid, "Customer ID": customid, "Order ID": order,
    #         "Tel": tel, "Box size": size, "file_type": extension, "token": encoded,
    #         "check_success": check_success}
    text1 = {'branch_cuscode5':'J!Z0M','camera_id': device, 'cus_group': 'walk pass', 'gender': 'male', 'count_person': person_pass, 'token': 'dkjfkdsjskfa'}
    # text2 = {'branch_cuscode5':'J!Z0M','camera_id': device, 'cus_group': 'walk pass', 'gender': 'female', 'count_person': person_in, 'token': 'dkjfkdsjskfa'}
    text3 = {'branch_cuscode5':'J!Z0M','camera_id': device, 'cus_group': 'walk in', 'gender': 'male', 'count_person': person_in, 'token': 'dkjfkdsjskfa'}
    # text4 = {'branch_cuscode5':'J!Z0M','camera_id': device, 'cus_group': 'walk in', 'gender': 'female', 'count_person': person_in, 'token': 'dkjfkdsjskfa'}
    print(text1)
    # response = requests.post(url, files=data, data=text)
    response1 = requests.post(url, data=text1)
    print('------posting------')
    if response1.ok:
        print("Upload completed successfully!")

    else:
        response1.raise_for_status()
        print("Something went wrong!")

    # response2 = requests.post(url, data=text2)
    # print('------posting------')
    # if response2.ok:
    #     print("Upload completed successfully!")
    #
    # else:
    #     response2.raise_for_status()
    #     print("Something went wrong!")
    #
    response3 = requests.post(url, data=text3)
    print('------posting------')
    if response3.ok:
        print("Upload completed successfully!")

    else:
        response3.raise_for_status()
        print("Something went wrong!")
    #
    # response4 = requests.post(url, data=text4)
    # print('------posting------')
    # if response4.ok:
    #     print("Upload completed successfully!")
    #
    # else:
    #     response4.raise_for_status()
    #     print("Something went wrong!")

def main(rtsp,device,line_ref_pri,line_ref_sec,save_video = False,cap_person_roi = False, post_to_server = False, cam_direction = None):
    cap = cv2.VideoCapture(rtsp)
    st = None
    record = 0

    W = None
    H = None
    ct = CentroidTracker(maxDisappeared=1, maxDistance=60)
    trackers = []
    trackableObjects = {}
    trackableObjects2 = {}
    totalFrames = 0
    totalout = 0
    totalin = 0
    totalpass = 0
    x = []
    empty = []
    empty1 = []
    old = 0
    old_pass = 0

    while True:
        create_folder()
        date = datetime.date.today()
        b = datetime.datetime.now().strftime("%T")
        ret,frame = cap.read()
        if ret == False:
            print('stop: {}'.format(rtsp))
            print('auto start!!!')
            os.execv(sys.executable, ['python'] + sys.argv)
            break
        frame = cv2.resize(frame,(640,360))
        frame_record = frame.copy()
        if W is None or H is None:
            (H, W) = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rects = []

        if st == None:
            st = time.time()
            st_post = time.time()
        et = time.time()

        if et - st > 0.1:
            # if totalFrames % 2 == 0:
            trackers = []

            if cam_direction == 'Y':
                roi = frame[0:H, line_ref_pri-line_ref_sec:line_ref_pri+line_ref_sec]
            elif cam_direction == 'X':
                roi = frame[0:H, 0:W]

            (H_roi, W_roi) = roi.shape[:2]
            results = model(roi, size=360)

            out2 = results.pandas().xyxy[0]

            if len(out2) != 0:
                rects = []
                for i in range(len(out2)):
                    xmin = int(out2.iat[i, 0])
                    ymin = int(out2.iat[i, 1])
                    xmax = int(out2.iat[i, 2])
                    ymax = int(out2.iat[i, 3])
                    obj_name = out2.iat[i, 6]

                    if obj_name != 'person':
                        continue
                    if obj_name == 'person' or obj_name == '0':
                        tracker = dlib.correlation_tracker()
                        rect = dlib.rectangle(xmin, ymin, xmax, ymax)
                        tracker.start_track(rgb, rect)

                        trackers.append(tracker)

                        if cap_person_roi == True:
                            person_img = frame_record[ymin:ymax, xmin:xmax]
                            (H_person, W_person) = person_img.shape[:2]
                            if H_person*W_person > 1000:
                                b = b.replace(':', '-')
                                b = str(b)
                                filename = 'backup_img/{}/device'.format(date) + str(device) + "t{}.jpg".format(b)
                                cv2.imwrite(filename, person_img)

            for tracker in trackers:
                tracker.update(rgb)
                pos = tracker.get_position()

                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())

                rects.append((startX, startY, endX, endY))
            if cam_direction == 'Y':
                cv2.line(frame, (line_ref_pri, 0), (line_ref_pri, H), (0, 0, 0), 3)
                cv2.line(frame, (line_ref_pri-line_ref_sec, 0), (line_ref_pri-line_ref_sec, H), (0, 0, 0), 3)
                cv2.line(frame, (line_ref_pri+line_ref_sec, 0), (line_ref_pri+line_ref_sec, H), (0, 0, 0), 3)
            elif cam_direction == 'X':
                cv2.line(frame, (0, line_ref_pri), (W, line_ref_pri), (0, 0, 0), 3)
                # cv2.line(frame, (0, line_ref_pri-line_ref_sec), (W, line_ref_pri-line_ref_sec), (0, 0, 0), 3)
                cv2.line(frame, (0, line_ref_pri+line_ref_sec), (W, line_ref_pri+line_ref_sec), (0, 0, 0), 3)
                cv2.line(frame, (320, 0), (320, H), (0, 0, 0), 3)
                cv2.line(frame, (0, 0), (0, H), (0, 0, 0), 3)

            # boundingboxes = np.array(rects)
            # boundingboxes = boundingboxes.astype(int)
            # rects = non_max_suppression_fast(boundingboxes, 0.3)
            objects = ct.update(rects)

            for (objectID, centroid) in objects.items():
                to = trackableObjects.get(objectID, None)
                to2 = trackableObjects2.get(objectID, None)

                if to is None:
                    to = TrackableObject(objectID, centroid)
                if to2 is None:
                    to2 = TrackableObject(objectID, centroid)
                else:
                    if cam_direction == 'Y':
                        y = [c[0] for c in to.centroids]

                        direction = centroid[0] - np.mean(y)
                    elif cam_direction == 'X':
                        x = [c[0] for c in to.centroids]

                        direction_x = centroid[0] - np.mean(x)
                        y = [c[1] for c in to.centroids]

                        direction_y = centroid[1] - np.mean(y)
                    to.centroids.append(centroid)
                    to2.centroids.append(centroid)

                    if not to.counted:
                        if cam_direction == 'Y':
                            if direction < -20 and ((W_roi // 2) - line_ref_sec < centroid[0] < W_roi // 2):
                                totalin += 1
                                print(objectID,direction)
                                to.counted = True

                            elif direction > 20 and ((W_roi // 2) + line_ref_sec > centroid[0] > W_roi // 2):
                                totalout += 1
                                print(objectID,direction)
                                to.counted = True
                        elif cam_direction == 'X':
                            if not to2.counted:
                                if (direction_x > 30 or direction_x < -30) and (580 > centroid[0] > 30) and (H_roi - line_ref_sec - line_ref_sec  > centroid[1]):
                                    totalpass += 1
                                    # print(objectID, direction_x)
                                    to2.counted = True
                                elif direction_y < -20 and (H_roi - line_ref_sec > centroid[1] > H_roi - line_ref_sec - line_ref_sec) and (580 > centroid[0] > 30):
                                    totalout += 1
                                    # print(objectID, direction_y)
                                    to2.counted = True

                            if (direction_y > 20 or direction_y < -20) and (H_roi > centroid[1] > H_roi - line_ref_sec - line_ref_sec) and (320 > centroid[0] > 0):
                                totalin += 1
                                # print(objectID, direction_y)
                                to.counted = True



                trackableObjects[objectID] = to
                trackableObjects2[objectID] = to2

                objectID = objectID + 1
                # cv2.rectangle(roi, (x1 - 5, y1), (x2 - 5, y2), (0, 0, 255), 2)
                text = "ID {}".format(objectID)
                cv2.putText(roi, text, (centroid[0] - 10, centroid[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                cv2.circle(roi, (centroid[0], centroid[1]), 4, (0, 0, 255), -1)

            if totalpass == 0 and old_pass == 0:
                conver_rate = 0.00
            else:
                conver_rate = ((totalin + old)/(totalpass + old_pass))*100

            info = [
                ("Conversion rate", '{:.2f}'.format(conver_rate)),
                ("Total person", totalpass + old_pass),
                ("Enter", totalin + old),
            ]

            for (i, (k, v)) in enumerate(info):
                text = "{}: {}".format(k, v)
                cv2.putText(frame, text, (10, H - ((i * 20) + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if save_video == True:
                if record == 0:
                    a = datetime.datetime.now().strftime("%T")
                    a = a.replace(':', '-')
                    a = str(a)
                    # st_vdo = time.time()

                    file = 'backup_video/{}/device'.format(date) + str(device) + "t{}.mp4".format(a)

                    video_size = (640, 360)
                    fourcc = cv2.VideoWriter_fourcc(*'H264')
                    rec = cv2.VideoWriter(file, fourcc, 30, video_size)

                    record = 1

                if record == 1:
                    rec.write(frame_record)
            st = time.time()
            cv2.imshow('{}'.format(rtsp), frame)

        if et - st_post > 60:
            # print(totalin,old)
            if post_to_server == True:
                request_post(totalin,totalpass,device)
            old += totalin
            old_pass += totalpass
            totalin = 0
            totalpass = 0
            st_post = time.time()

        k = cv2.waitKey(1)
        if k == ord('q') or b > '22:30:00':
        # if k == ord('q'):
            print('exit program !!!')
            break
        # totalFrames += 1
    cap.release()
    if record == 1:
        rec.release()
    cv2.destroyAllWindows()

def main_threading(rtsp,device,line_ref_pri,line_ref_sec,save_video,cap_person_roi,post_to_server,cam_direction):
    t1 = Thread(target=main, args=(rtsp,device,line_ref_pri,line_ref_sec,save_video,cap_person_roi,post_to_server,cam_direction,))
    t1.start()

if __name__ == '__main__':
    print('start load model!!!')
    model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
    model.conf = 0.2
    model.iou = 0.4
    model.classes = [0]  # (optional list) filter by class, i.e. = [0, 15, 16] for COCO persons, cats and dogs
    model.amp = True  # Automatic Mixed Precision (AMP) inference

    print('load yolov5 successfully!!!')

    main(rtsp='rtsp://testcam:password01@192.168.1.230:554/cam/realmonitor?channel=4&subtype=0',
         device='test',
         line_ref_pri=300,
         line_ref_sec=50,
         save_video=False,
         cap_person_roi=False,
         post_to_server=False,
         cam_direction='X')

    # main(rtsp=0,
    #      device=14,
    #      line_ref_pri=130,
    #      line_ref_sec=50,
    #      save_video=False,
    #      cap_person_roi=True,
    #      post_to_server=False,
    #      cam_direction='X')

    # main_threading(rtsp='rtsp://test:advice128@110.49.125.237:554/cam/realmonitor?channel=1&subtype=0',
    #                device=1,
    #                line_ref_pri = 160,
    #                line_ref_sec = 50,
    #                save_video=False,
    #                cap_person_roi=False,
    #                post_to_server=True,
    #                cam_direction='X')

    # main_threading(rtsp='rtsp://admin:888888@192.168.7.50:10554/tcp/av0_0',
    #                device=2,
    #                line_ref_pri=0,
    #                line_ref_sec=100,
    #                save_video=False,
    #                cap_person_roi=False,
    #                post_to_server=False,
    #                cam_direction='Y')
    # main_threading(rtsp='rtsp://testcam:Password1@advicedvrddns.ddns.net:554/cam/realmonitor?channel=14&subtype=0',
    #                device=14,
    #                line_ref_pri=130,
    #                line_ref_sec=50,
    #                save_video=False,
    #                cap_person_roi=False,
    #                post_to_server=False,
    #                cam_direction='X')
    #
    # main_threading(rtsp='rtsp://testcam:Password1@advicedvrddns.ddns.net:554/cam/realmonitor?channel=15&subtype=0',
    #                device=15,
    #                line_ref_pri=450,
    #                line_ref_sec=20,
    #                save_video=False,
    #                cap_person_roi=False,
    #                post_to_server=False,
    #                cam_direction='Y')