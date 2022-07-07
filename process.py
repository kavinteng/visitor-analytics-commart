from module import *

def run_config():
    rtsp_list_array,device_name_array = read_nvr(5)
    root = Tk()
    root.title('Edit_polygon')
    root.geometry('250x300+0+0')

    for i in rtsp_list_array:
        ch1 = Button(root, text="CH{}".format(rtsp_list_array.index(i)+1), width=20, bg='red', fg='white', command=lambda
            cam=i: set_polycon_tk(cam))
        ch1.pack(padx=5, pady=5)

    root.mainloop()

def confirm_yesno(message = 'ยืนยันที่จะปิดโปรแกรมหรือไม่'):
    if messagebox.askyesno(title='confirmation',message=message):
        root.destroy()
        sys.exit(1)

def run_app():
    rtsp_list_array,device_name_array = read_nvr(5)
    for j in rtsp_list_array:
        cam_threading(j,device_name_array[rtsp_list_array.index(j)])

if __name__ == '__main__':
    write_nvr()
    auto_start = read_nvr(6)
    if os.path.isfile('logfile.db') == False:
        create_logfile()
    load_all_model()
    root = Tk()
    root.title('Application Controller')
    root.geometry('250x300+0+0')
    if auto_start == 'TRUE':
        run_app()
    elif auto_start == 'FALSE':
        start_app = Button(root, text="START", width=20, bg='red', fg='white', command=run_app)
        start_app.pack(padx=5, pady=5)
    edit_poly = Button(root, text="Edit_polygon", width=20, bg='red', fg='white', command=run_config)
    edit_poly.pack(padx=5, pady=5)

    admin = Button(root, text="ADMIN", width=20, bg='red', fg='white', command=admin_control)
    admin.pack(padx=5, pady=5, side="bottom")

    root.protocol('WM_DELETE_WINDOW', confirm_yesno)
    # root.attributes('-topmost', True)

    root.mainloop()