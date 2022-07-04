import cv2
import os
import torch
import time
import numpy as np
import datetime
import csv
import shutil
import os
import requests, json
import sqlite3
from configparser import ConfigParser
from threading import Thread
import gdown
import pathlib
from tkinter import messagebox
from tkinter import *
import ast
import tkinter.simpledialog

def load_all_model():
    global MODEL_MEAN_VALUES,ageList,genderList,faceNet,ageNet,genderNet,model
    print('start load model!!!')
    model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
    model.conf = 0.2
    model.iou = 0.4
    model.classes = [0]
    model.amp = True
    print('load yolov5 successfully!!!')

    print('load gender & age model')
    if os.path.isdir('gender_age_model') == False:
        url = "https://drive.google.com/drive/u/1/folders/1n7WSJV0CdGY8vaPukLxZDXT3TjzEZ-Hp"
        gdown.download_folder(url)

    faceProto="gender_age_model/opencv_face_detector.pbtxt"
    faceModel="gender_age_model/opencv_face_detector_uint8.pb"
    ageProto="gender_age_model/age_deploy.prototxt"
    ageModel="gender_age_model/age_net.caffemodel"
    genderProto="gender_age_model/gender_deploy.prototxt"
    genderModel="gender_age_model/gender_net.caffemodel"

    MODEL_MEAN_VALUES=(78.4263377603, 87.7689143744, 114.895847746)
    ageList=['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']
    genderList=['Male','Female']

    faceNet=cv2.dnn.readNet(faceModel,faceProto)
    ageNet=cv2.dnn.readNet(ageModel,ageProto)
    genderNet=cv2.dnn.readNet(genderModel,genderProto)
    print('load gender & age successfully!!!')

def cam_threading(rtsp_url,num):
    cap = cv2.VideoCapture(rtsp_url)
    if cap.isOpened():
        t = Thread(target=get_rtsp, args=(rtsp_url,num,))
        t.start()
        return True
    else:
        return False

def get_rtsp(rtsp_url,num,st=None):
    # 'rtsp://admin:888888@192.168.1.50:10554/tcp/av0_0'
    cap = cv2.VideoCapture(rtsp_url)
    print(f'start cam: {rtsp_url}')
    while True:
        ret,frame = cap.read()
        if ret == False:
            print(f'stop {rtsp_url}')
            print('auto start!!!')
            os.execv(sys.executable, ['python'] + sys.argv)
            break
        frame = cv2.resize(frame, (640, 360))
        if st == None:
           st = time.time()
        et = time.time()
        time_ref = read_nvr(4)
        if et - st > int(time_ref):
            save_img = read_nvr(3)
            polygon_employ, polygon_customer = read_polygon_value(rtsp_url)
            if polygon_employ != False:
                if type(polygon_employ) == str:
                    polygon_employ = ast.literal_eval(polygon_employ)
                    polygon_customer = ast.literal_eval(polygon_customer)
                Date = datetime.datetime.now().strftime("%d/%m/%Y")
                Time = datetime.datetime.now().strftime("%T")

                file_name = Time.replace(':', '-')
                file_name = num + '_' + file_name
                date_img = build_folder_file()
                img_file = date_img + '/' + file_name + '.jpg'
                if save_img == 'TRUE':
                    cv2.imwrite(img_file, frame)
                output_flask_process, output_flask_process_gender_age,check_break = request_post_onprocess(num, frame, Date, Time,
                                                                                               file_name,
                                                                                               polygon_customer,
                                                                                               polygon_employ, model)
                # print(output_flask_process, output_flask_process_gender_age)
                st = time.time()
                if check_break == True:
                    break
            else:
                print('No polygon stop {}'.format(rtsp_url))
                break

def build_folder_file():
    base_dir = pathlib.Path(__file__).parent.absolute()
    backup_img = os.path.join(base_dir, "backup_file")
    date_img = os.path.join(backup_img, "{}".format(datetime.date.today()))

    if os.path.isdir(backup_img) == False:
        os.mkdir(backup_img)
    if os.path.isdir(f'{date_img}') == False:
        os.mkdir(date_img)
    # try:
    #     with open('backup_file/Head-count(not for open).csv') as f:
    #         pass
    # except:
    #     header = ['device_name','File name', 'วัน', 'เวลา', 'จำนวนคนทั้งหมด', 'พนักงาน advice', 'ลูกค้า', 'จำนวนคนที่เดินผ่าน',
    #               'POST STATUS']
    #     with open('backup_file/Head-count(not for open).csv', 'w', encoding='UTF-8-sig', newline='') as f:
    #         writer = csv.writer(f)
    #         writer.writerow(header)

    return date_img

def request_post_onprocess(device_name,frame,date,time,file_name, polygon_nodetect, polygon_employ, model):
    camera_opened = read_nvr(2)
    employee = 0
    customer = 0
    walking_pass = 0
    gender_array = []
    age_array = []
    count_men = 0
    count_women = 0
    count0_2 = 0
    count4_6 = 0
    count8_12 = 0
    count15_20 = 0
    count25_32 = 0
    count38_43 = 0
    count48_53 = 0
    count60_100 = 0
    output = []
    check_break = False

    url = 'https://globalapi.advice.co.th/api/upload_people'
    # url = None

    # try:
    #     repost_logfile(url)
    # except:
    #     pass
    frame_gender = frame.copy()
    results = model(frame, size=640)
    out2 = results.pandas().xyxy[0]

    if len(out2) != 0:
        for i in range(len(out2)):
            xmin = int(out2.iat[i, 0])
            ymin = int(out2.iat[i, 1])
            xmax = int(out2.iat[i, 2])
            ymax = int(out2.iat[i, 3])

            cenx = (xmax + xmin) // 2
            ceny = (ymax + ymin) // 2
            obj_name = out2.iat[i, 6]
            if obj_name == 'person' or obj_name == '0':

                frame_face = frame_gender[ymin:ymax, xmin:xmax]
                # gender_array,age_array = gender_age(frame_face,faceNet,ageNet,genderNet,gender_array,age_array)

                color = draw_polygon(cenx, ceny, polygon_nodetect, polygon_employ)

                if color == (0, 0, 255):
                    employee += 1
                elif color == (255, 0, 0):
                    customer += 1
                elif color == (0, 255, 0):
                    walking_pass += 1
                elif color == (0, 0, 0):
                    pass

        count_men = gender_array.count('Male')
        count_women = gender_array.count('Female')

        count0_2 = age_array.count('(0-2)')
        count4_6 = age_array.count('(4-6)')
        count8_12 = age_array.count('(8-12)')
        count15_20 = age_array.count('(15-20)')
        count25_32 = age_array.count('(25-32)')
        count38_43 = age_array.count('(38-43)')
        count48_53 = age_array.count('(48-53)')
        count60_100 = age_array.count('(60-100)')

    count_all_json = employee+customer+walking_pass
    dd, mm, yyyy = date.split('/')
    date_json = f'{yyyy}-{mm}-{dd}'
    time_json = date_json + f' {time}'

    output_flask_process = {"people_device": device_name,"img_name": file_name, "img_date": date_json, "img_time": time_json,
                            "people_total": count_all_json, "people_advice": employee,
                            "people_other": customer, "storefront": walking_pass}

    output_flask_process_gender_age = {"count_male": count_men, "count_female": count_women,
                                       "(0-2)": count0_2,'(4-6)': count4_6,'(8-12)':count8_12,
                                       '(15-20)': count15_20,'(25-32)': count25_32,'(38-43)':count38_43,
                                       '(48-53)': count48_53,'(60-100)': count60_100}

    text = {"Status_post": 'Addlog'}
    # addlog(device_name, file_name, date_json, time_json, count_all_json, employee, customer, walking_pass)
    status_post = request_post(url, output_flask_process)
    if status_post == 0:
        text['Status_post'] = 'No'
        print(output_flask_process, text)
        addlog(device_name, file_name, date_json, time_json, count_all_json, employee, customer, walking_pass)
    elif status_post == 1:
        text['Status_post'] = 'Yes'
        print(output_flask_process, text)
    elif status_post == 2:
        text['Status_post'] = 'empty url'
        print(output_flask_process, text)

    # --------------------------------------------------------
    # status_post_csv = text['Status_post']
    # output.append([device_name,file_name, date_json, time_json, count_all_json, employee, customer, walking_pass, status_post_csv])
    # build_csv(output)
    if camera_opened == 'TRUE':
        cv2.imshow(f'{device_name}', frame)
        k = cv2.waitKey(1)
        if k == ord('q'):
            check_break = True
            cv2.destroyWindow(f'{device_name}')


    return output_flask_process, output_flask_process_gender_age,check_break

def draw_polygon(cenx, ceny, polygon1, polygon2):
    contours1 = np.array(polygon1)
    contours2 = np.array(polygon2)
    array_miny = []
    for val in polygon1:
        array_miny.append(val[1])
    for val2 in polygon2:
        array_miny.append(val2[1])
    image = np.zeros((360, 640, 3))
    cv2.fillPoly(image, pts=[contours1], color=(2, 255, 255))
    cv2.fillPoly(image, pts=[contours2], color=(1, 0, 255))
    if int(image[ceny, cenx, 0]) == 1:
        color = (0, 0, 255)
    elif int(image[ceny, cenx, 0]) == 2:
        color = (255, 0, 0)
    elif ceny > min(array_miny):
        color = (0, 255, 0)
    else:
        color = (0, 0, 0)
    # cv2.imshow("filledPolygon", image)
    return color

def highlightFace(net, frame, conf_threshold=0.7):
    frameOpencvDnn=frame.copy()
    frameHeight=frameOpencvDnn.shape[0]
    frameWidth=frameOpencvDnn.shape[1]
    blob=cv2.dnn.blobFromImage(frameOpencvDnn, 1.0, (300, 300), [104, 117, 123], True, False)

    net.setInput(blob)
    detections=net.forward()
    faceBoxes=[]
    for i in range(detections.shape[2]):
        confidence=detections[0,0,i,2]
        if confidence>conf_threshold:
            x1=int(detections[0,0,i,3]*frameWidth)
            y1=int(detections[0,0,i,4]*frameHeight)
            x2=int(detections[0,0,i,5]*frameWidth)
            y2=int(detections[0,0,i,6]*frameHeight)
            faceBoxes.append([x1,y1,x2,y2])
            cv2.rectangle(frameOpencvDnn, (x1,y1), (x2,y2), (0,255,0), int(round(frameHeight/150)), 8)
    return frameOpencvDnn,faceBoxes

def gender_age(frame,faceNet,ageNet,genderNet,gender_array,age_array):
    # padding = 20
    # resultImg, faceBoxes = highlightFace(faceNet, frame)
    # if not faceBoxes:
    #     print("No face detected")

    # for faceBox in faceBoxes:
    #     face = frame[max(0, faceBox[1] - padding):
    #                  min(faceBox[3] + padding, frame.shape[0] - 1), max(0, faceBox[0] - padding)
    #                                                                 :min(faceBox[2] + padding, frame.shape[1] - 1)]

    blob = cv2.dnn.blobFromImage(frame, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
    genderNet.setInput(blob)
    genderPreds = genderNet.forward()
    gender = genderList[genderPreds[0].argmax()]
    gender_array.append(gender)

    ageNet.setInput(blob)
    agePreds = ageNet.forward()
    age = ageList[agePreds[0].argmax()]
    age_array.append(age)

    return gender_array,age_array

def create_logfile():
    con = sqlite3.connect('logfile.db')
    cur = con.cursor()
    cur.execute('''CREATE TABLE log
                   (people_device char(7), img_name char(15), img_date char(15), img_time char(15), 
                   people_total int, people_advice int, people_other int, storefront int)''')

    con.commit()
    con.close()

def addlog(device_name,file_json,date_json,time_json,count_all_json,store_emp,store_cus,store_walkpass):
    con = sqlite3.connect('logfile.db')
    cur = con.cursor()
    sql = '''INSERT INTO log(people_device, img_name, img_date, img_time,
                   people_total, people_advice, people_other, storefront) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
    task = (device_name,file_json,date_json,time_json,count_all_json,store_emp,store_cus,store_walkpass)
    cur.execute(sql, task)
    con.commit()
    con.close()

def repost_logfile(url):
    con = sqlite3.connect('logfile.db')
    cur = con.cursor()
    array = []
    for row in cur.execute('SELECT * FROM log'):
        device_name, file_json, date_json, time_json, count_all_json, store_emp, store_cus, store_walkpass = row
        array.append([device_name, file_json, date_json, time_json, count_all_json, store_emp, store_cus, store_walkpass])

    for row_store in array:
        text_for_post = {"people_device": row_store[0], "img_name": row_store[1], "img_date": row_store[2],
                         "img_time": row_store[3],"people_total": row_store[4], "people_advice": row_store[5],
                         "people_other": row_store[6],"storefront": row_store[7]}
        status_post = request_post(url, text_for_post)
        if status_post == 1:
            print(text_for_post)
            # print('repost successfully')
            cur.execute("DELETE FROM log WHERE img_time=? and people_device=?",(row_store[3],row_store[0],))
            con.commit()

    con.close()

def request_post(url, text):
    if url == None:
        status_post = 2
    else:
        response = requests.post(url, json=text)
        print('\n------posting------')
        if response.ok:
            print("Upload completed successfully!")
            status_post = 1

        else:
            print("Fall upload!")
            response.status_code
            status_post = 0

    return status_post

def read_polygon_value(num):
    read_config = ConfigParser()
    read_config.read('config.ini')
    if read_config.has_option(f'polygon: {num}', 'polygon_employee') == True:
        polygon_employ = read_config.get(f'polygon: {num}', 'polygon_employee')
        polygon_customer = read_config.get(f'polygon: {num}', 'polygon_customer')
        return polygon_employ, polygon_customer
    else:
        return False,False

def admin_control():
    global admin_root
    Tk().withdraw()
    while True:
        passw = tkinter.simpledialog.askstring("Password", "Enter password:", show='*')
        if passw == 'Advice#128' or passw == None:
            break
    if passw == 'Advice#128':
        admin_root = Tk()
        admin_root.geometry('200x200+0+400')
        admin_root.title('ADMIN_Controller')
        num_report = Label(admin_root, text='ADMIN-CONTROLLER', fg='red', font=('Arial', 12))
        num_report.pack(padx=5, pady=5)
        git_c = Button(admin_root, text="git pull", width=20, bg='red', fg='white', command=git_c_botton)
        git_c.pack(padx=5, pady=5)
        restart = Button(admin_root, text="restart", width=20, bg='red', fg='white', command=restart_botton)
        restart.pack(padx=5, pady=5)
        admin_root.mainloop()

def git_c_botton():
    out = os.system('git pull')
    if out == 0:
        os.execv(sys.executable, ['python'] + sys.argv)
    elif out == 1:
        git_pull_fall = Label(admin_root, text='git pull fall', fg='red', font=('Arial', 10))
        git_pull_fall.pack(padx=5, pady=5)

def restart_botton():
    os.execv(sys.executable, ['python'] + sys.argv)

def set_polygon(rtsp_url):
    global poly1,poly2, img
    size_img_vdo = (640, 360)
    cap = cv2.VideoCapture(rtsp_url)
    poly1 = []
    poly2 = []
    check_click = 0

    while True:
        _, img = cap.read()
        img = cv2.resize(img, size_img_vdo)
        if check_click == 2:
            contours1 = np.array(result1)
            contours2 = np.array(result2)
            cv2.fillPoly(img, pts=[contours2], color=(2, 255, 255))
            cv2.fillPoly(img, pts=[contours1], color=(1, 0, 255))
        # cv2.fillPoly(img, pts=[result3], color=(3, 0, 255))
        for x,y in poly1:
            cv2.putText(img, str(x) + ',' +
                        str(y), (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 0, 0), 2)
        for x,y in poly2:
            cv2.putText(img, str(x) + ',' +
                        str(y), (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 0, 0), 2)
        cv2.imshow('image', img)
        cv2.setMouseCallback('image', click_event)
        k = cv2.waitKey(1)
        if k == ord('q') and (check_click ==3): #q
            break
        elif k == ord('d'): #d
            print('clear array')
            poly1 = []
            poly2 = []
            check_click = 0
        elif k == ord('z') and (check_click ==0): #z
            print('save poly1')
            result1 = poly1
            poly1 = []
            poly2 = []
            check_click += 1
        elif k == ord('x') and (check_click ==1): #x
            print('save poly2')
            result2 = poly2
            poly1 = []
            poly2 = []
            check_click += 1
        elif k == ord('c') and (check_click ==2): #c
            try:
                print(f'check array\n{result1}\n{result2}')
                check_click += 1
            except:
                print(f'Non save value: {poly1}')
        else:
            pass
        # close the window
    cv2.destroyAllWindows()

    return result1, result2

def click_event(event, x, y, flags, params):
    global poly1,poly2, img
    if event == cv2.EVENT_LBUTTONDOWN:
        font = cv2.FONT_HERSHEY_SIMPLEX
        # print(x, ",", y)
        cv2.putText(img, str(x) + ',' +
                    str(y), (x, y), font,
                    1, (255, 0, 0), 2)
        poly1.append([x, y])
        poly2.append([x, y])
        cv2.imshow('image', img)

def set_polygon_zone(num):
    config = ConfigParser()
    config.read('config.ini')
    if config.has_section(f'polygon: {num}') == False:
        config.add_section(f'polygon: {num}')
    if config.has_option(f'polygon: {num}','polygon_employee') == False:
        polygon_employ,polygon_customer = set_polygon(num)
        config.set(f'polygon: {num}','polygon_employee',str(polygon_employ))
        config.set(f'polygon: {num}', 'polygon_customer',str(polygon_customer))
        cfgfile = open('config.ini', 'w')
        config.write(cfgfile)
        cfgfile.close()
    else:
        polygon_employ = config.get(f'polygon: {num}','polygon_employee')
        polygon_customer = config.get(f'polygon: {num}', 'polygon_customer')
    return polygon_employ,polygon_customer

def write_nvr():
    write_config = ConfigParser()
    write_config.read('config.ini')
    if write_config.has_section('BASE CONFIG') == False:
        write_config.add_section('BASE CONFIG')
        write_config.set('BASE CONFIG', 'rtsp_source','rtsp://testcam:Password1@advicedvrddns.ddns.net:554/cam/realmonitor?')
        write_config.set('BASE CONFIG', 'camera opened', 'TRUE')
        write_config.set('BASE CONFIG', 'save image result', 'FALSE')
        write_config.set('BASE CONFIG', 'time ref', '10')
        cfgfile = open('config.ini','w')
        write_config.write(cfgfile)
        cfgfile.close()

def read_nvr(check):
    read_config = ConfigParser()
    read_config.read('config.ini')
    if check == 1:
        rtsp_source = read_config.get('BASE CONFIG','rtsp_source')
        return rtsp_source
    elif check == 2:
        camera_opened = read_config.get('BASE CONFIG', 'camera opened')
        return camera_opened
    elif check == 3:
        save_img = read_config.get('BASE CONFIG', 'save image result')
        return save_img
    elif check == 4:
        time_ref = read_config.get('BASE CONFIG', 'time ref')
        return time_ref

def set_polycon_tk(rtsp):
    # rtsp_source = read_nvr(1)
    # rtsp_split = rtsp_source.split('/')
    # if type(num) == int:
    #     rtsp = num
    # elif num == 'rtsp://admin:888888@192.168.7.60:10554/tcp/av0_1':
    #     rtsp = num
    # else:
    #     rtsp = '{}//{}/{}/{}'.format(rtsp_split[0],rtsp_split[2],rtsp_split[3],num)
    cap = cv2.VideoCapture(rtsp)
    if cap.isOpened():
        polygon_employ, polygon_customer = set_polygon_zone(rtsp)
        size_img_vdo = (640, 360)
        while True:
            _,frame = cap.read()
            frame = cv2.resize(frame,size_img_vdo)
            if type(polygon_employ) == str:
                polygon_employ = ast.literal_eval(polygon_employ)
                polygon_customer = ast.literal_eval(polygon_customer)
            contours1 = np.array(polygon_employ)
            contours2 = np.array(polygon_customer)
            cv2.fillPoly(frame, pts=[contours2], color=(2, 255, 255))
            cv2.fillPoly(frame, pts=[contours1], color=(1, 0, 255))


            cv2.imshow('result_polygon',frame)
            k = cv2.waitKey(1)
            if k == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()