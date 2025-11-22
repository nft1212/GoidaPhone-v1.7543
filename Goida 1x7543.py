import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Frame, Label, Button, Entry, Listbox, Scrollbar, Canvas
import socket
import threading
import time
import pyaudio
import queue
import winsound
import json
import os
import secrets
from datetime import datetime
import numpy as np
import configparser
import wave
import subprocess
import sys
import select
try:
    from win32api import GetSystemMetrics
    from win32gui import GetWindowText, GetForegroundWindow
    from win32con import MB_ICONINFORMATION
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class WinXPStyle:
    @staticmethod
    def create_frame(parent, **kwargs):
        return Frame(parent, bg='#d4d0c8', **kwargs)
    
    @staticmethod
    def create_button(parent, text, **kwargs):
        return Button(parent, text=text, bg='#d4d0c8', fg='black', 
                     font=('Tahoma', 8), relief='raised', bd=2, **kwargs)
    
    @staticmethod
    def create_label(parent, text, **kwargs):
        return Label(parent, text=text, bg='#d4d0c8', fg='black', 
                    font=('Tahoma', 8), **kwargs)
    
    @staticmethod
    def create_entry(parent, **kwargs):
        return Entry(parent, bg='white', fg='black', font=('Tahoma', 8),
                   relief='sunken', bd=1, **kwargs)

class GoidaPhone:
    def __init__(self, root):
        self.root = root
        self.root.title("GoidaPhone v1.7543")
        self.root.geometry("900x650")
        self.root.configure(bg='#008080')
        self.root.resizable(True, True)
        
        # Устанавливаем иконку (симуляция)
        try:
            self.root.iconbitmap(default='system.ico')
        except:
            pass
        
        # Конфигурация
        self.host_ip = self._get_local_ip()
        self.udp_port = 17385
        self.tcp_port = 17386
        self.username = os.getenv('USERNAME', f"Пользователь_{secrets.randbelow(1000):03d}")
        
        # Аудио настройки
        self.audio = pyaudio.PyAudio()
        self.input_device_index = None
        self.output_device_index = None
        self.stream_in = None
        self.stream_out = None
        self.recording = False
        self.playing = False
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio_buffer = queue.Queue()
        self.volume = 1.0
        self.mic_test_active = False
        self.speaker_test_active = False
        
        # Сеть
        self.udp_socket = None
        self.voice_socket = None
        self.in_voice_chat = False
        self.target_ip = None
        self.peers = {}
        self.last_broadcast_time = 0
        self.user_join_times = {}
        
        # Окно звонка
        self.call_window = None
        self.call_timer = None
        
        # Загружаем настройки
        self._load_settings()
        
        # Создаем интерфейс
        self._create_winxp_interface()
        self._start_networking()
        
        self._add_log("СИСТЕМА", f"GoidaPhone v1.7543 запущен", "system")
        self._add_log("СИСТЕМА", f"Ваш IP: {self.host_ip}", "system")
        self._add_log("СИСТЕМА", f"Имя пользователя: {self.username}", "system")
        
        # Таймер для проверки уведомлений
        if HAS_WIN32:
            self.root.after(1000, self._check_notifications)

    def _check_notifications(self):
        """Проверяем необходимость показа уведомлений"""
        if HAS_WIN32 and not self._is_window_focused() and hasattr(self, 'pending_notification'):
            self._show_windows_notification()
            delattr(self, 'pending_notification')
        self.root.after(1000, self._check_notifications)

    def _is_window_focused(self):
        """Проверяем, активно ли наше окно"""
        if not HAS_WIN32:
            return True
        return GetWindowText(GetForegroundWindow()) == "GoidaPhone v1.7543"

    def _show_windows_notification(self):
        """Показываем уведомление Windows"""
        if HAS_WIN32:
            try:
                win32gui.MessageBox(0, "Новое сообщение в GoidaPhone", "GoidaPhone", MB_ICONINFORMATION)
            except:
                pass

    def _get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"

    def _load_settings(self):
        self.config = configparser.ConfigParser()
        self.config_file = "goidaphone.ini"
        
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                if 'Audio' in self.config:
                    input_idx = self.config.get('Audio', 'input_device', fallback='')
                    if input_idx and input_idx != 'None' and input_idx != '':
                        self.input_device_index = int(input_idx)
                    else:
                        self.input_device_index = None
                    
                    output_idx = self.config.get('Audio', 'output_device', fallback='')
                    if output_idx and output_idx != 'None' and output_idx != '':
                        self.output_device_index = int(output_idx)
                    else:
                        self.output_device_index = None
                    
                    self.volume = self.config.getfloat('Audio', 'volume', fallback=0.8)
                    self.sample_rate = self.config.getint('Audio', 'sample_rate', fallback=16000)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def _save_settings(self):
        try:
            if not hasattr(self, 'config'):
                self.config = configparser.ConfigParser()
            
            self.config['Audio'] = {
                'input_device': str(self.input_device_index) if self.input_device_index is not None else '',
                'output_device': str(self.output_device_index) if self.output_device_index is not None else '',
                'volume': str(self.volume),
                'sample_rate': str(self.sample_rate)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def _create_winxp_interface(self):
        # Main frame with XP style
        main_frame = Frame(self.root, bg='#d4d0c8', relief='sunken', bd=2)
        main_frame.pack(fill='both', expand=True, padx=4, pady=4)
        
        # Title bar
        title_frame = Frame(main_frame, bg='#0a246a', relief='raised', bd=1)
        title_frame.pack(fill='x', pady=(0, 4))
        
        icon_label = Label(title_frame, text="📞", bg='#0a246a', fg='white', 
                          font=('Tahoma', 12), padx=8)
        icon_label.pack(side='left')
        
        title = Label(title_frame, text="GoidaPhone v1.7543 - Winora Company", 
                     bg='#0a246a', fg='white', font=('Tahoma', 10, 'bold'), pady=3)
        title.pack(side='left', fill='x', expand=True)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self._show_help)
        help_menu.add_command(label="Очистить чат", command=self._clear_chat)
        
        # Status bar
        status_frame = Frame(main_frame, bg='#d4d0c8', relief='sunken', bd=1)
        status_frame.pack(fill='x', side='bottom', pady=(4, 0))
        
        self.connection_light = Canvas(status_frame, width=16, height=16, bg='#d4d0c8', 
                                     highlightthickness=0)
        self.connection_light.create_oval(2, 2, 14, 14, fill='green', outline='black')
        self.connection_light.pack(side='left', padx=5, pady=2)
        
        self.status_var = tk.StringVar(value="Сеть: АКТИВНА | Пользователей: 0")
        status_label = Label(status_frame, textvariable=self.status_var, bg='#d4d0c8', 
                           fg='black', font=('Tahoma', 8), anchor='w')
        status_label.pack(side='left', padx=5, fill='x', expand=True)
        
        # Main content
        content = Frame(main_frame, bg='#d4d0c8')
        content.pack(fill='both', expand=True, padx=4, pady=4)
        
        # Left panel
        left_panel = Frame(content, bg='#d4d0c8')
        left_panel.pack(side='left', fill='y', padx=(0, 4))
        
        # Users list
        user_frame = Frame(left_panel, bg='#d4d0c8', relief='sunken', bd=1)
        user_frame.pack(fill='both', expand=True, pady=(0, 4))
        
        user_header = Frame(user_frame, bg='#3a6ea5', relief='raised', bd=1)
        user_header.pack(fill='x', pady=(0, 4))
        
        Label(user_header, text="👥 Активные пользователи", bg='#3a6ea5', fg='white',
             font=('Tahoma', 9, 'bold'), pady=2).pack()
        
        list_frame = Frame(user_frame, bg='#d4d0c8')
        list_frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        self.user_listbox = Listbox(list_frame, bg='white', fg='black',
                                  selectbackground='#3a6ea5', selectforeground='white',
                                  font=('Tahoma', 8), relief='sunken', bd=1)
        
        scrollbar = Scrollbar(list_frame, orient='vertical')
        self.user_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.user_listbox.yview)
        
        self.user_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right panel
        right_panel = Frame(content, bg='#d4d0c8')
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Chat area
        chat_frame = Frame(right_panel, bg='#d4d0c8')
        chat_frame.pack(fill='both', expand=True)
        
        chat_header = Frame(chat_frame, bg='#3a6ea5', relief='raised', bd=1)
        chat_header.pack(fill='x', pady=(0, 4))
        
        Label(chat_header, text="💬 Чат", bg='#3a6ea5', fg='white',
             font=('Tahoma', 9, 'bold'), pady=2).pack()
        
        self.chat_text = scrolledtext.ScrolledText(chat_frame, wrap='word', bg='white',
                                                 fg='black', font=('Tahoma', 8),
                                                 relief='sunken', bd=1)
        self.chat_text.pack(fill='both', expand=True, padx=2, pady=2)
        self.chat_text.config(state='disabled')
        
        # Input area
        input_frame = Frame(right_panel, bg='#d4d0c8')
        input_frame.pack(fill='x', pady=4, padx=2)
        
        self.message_var = tk.StringVar()
        msg_entry = Entry(input_frame, textvariable=self.message_var, bg='white',
                        fg='black', font=('Tahoma', 9), relief='sunken', bd=1)
        msg_entry.pack(side='left', fill='x', expand=True, padx=(0, 4))
        msg_entry.bind('<Return>', self._send_message)
        
        send_btn = Button(input_frame, text="Отправить", command=self._send_message,
                        bg='#d4d0c8', fg='black', font=('Tahoma', 8), relief='raised',
                        bd=2, width=10)
        send_btn.pack(side='right')
        
        # Control buttons
        control_frame = Frame(right_panel, bg='#d4d0c8')
        control_frame.pack(fill='x', pady=4)
        
        btn_frame = Frame(control_frame, bg='#d4d0c8')
        btn_frame.pack()
        
        self.call_btn = Button(btn_frame, text="📞 Звонок", command=self._start_call,
                             bg='#d4d0c8', fg='black', font=('Tahoma', 8), relief='raised',
                             bd=2, width=12)
        self.call_btn.pack(side='left', padx=2)
        
        self.hangup_btn = Button(btn_frame, text="📞 Завершить", command=self._stop_call,
                               bg='#d4d0c8', fg='black', font=('Tahoma', 8), relief='raised',
                               bd=2, width=12, state='disabled')
        self.hangup_btn.pack(side='left', padx=2)
        
        Button(btn_frame, text="🔄 Сканировать", command=self._discover_peers,
              bg='#d4d0c8', fg='black', font=('Tahoma', 8), relief='raised',
              bd=2, width=12).pack(side='left', padx=2)
        
        Button(btn_frame, text="⚙ Настройки", command=self._show_settings,
              bg='#d4d0c8', fg='black', font=('Tahoma', 8), relief='raised',
              bd=2, width=12).pack(side='left', padx=2)

    def _start_networking(self):
        try:
            # UDP сокет для широковещательных сообщений
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            self.udp_socket.setblocking(False)
            
            # TCP сокет для голосовых соединений
            self.voice_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.voice_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.voice_listener.bind(('0.0.0.0', self.tcp_port))
            self.voice_listener.listen(5)
            self.voice_listener.setblocking(False)
            
            # Запускаем потоки
            threading.Thread(target=self._udp_listener, daemon=True).start()
            threading.Thread(target=self._voice_accept_loop, daemon=True).start()
            threading.Thread(target=self._ping_loop, daemon=True).start()
            
        except Exception as e:
            self._add_log("ОШИБКА", f"Ошибка сети: {e}", "error")

    def _udp_listener(self):
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                if addr[0] != self.host_ip:
                    try:
                        message = json.loads(data.decode('utf-8'))
                        self._handle_network_message(addr[0], message)
                    except:
                        pass
            except socket.error:
                time.sleep(0.01)

    def _voice_accept_loop(self):
        while True:
            try:
                readable, _, _ = select.select([self.voice_listener], [], [], 0.1)
                if readable:
                    conn, addr = self.voice_listener.accept()
                    if not self.in_voice_chat and addr[0] != self.host_ip:
                        self._handle_incoming_call(conn, addr)
                    else:
                        conn.close()
            except:
                time.sleep(0.1)

    def _ping_loop(self):
        while True:
            current_time = time.time()
            
            # Удаляем неактивных пользователей
            for ip in list(self.peers.keys()):
                if current_time - self.peers[ip]['last_seen'] > 30:
                    username = self.peers[ip]['username']
                    del self.peers[ip]
                    self._update_user_list()
                    self._add_log("СИСТЕМА", f"Пользователь {username} отключился", "system")
            
            # Отправляем широковещательное сообщение каждые 10 секунд
            if current_time - self.last_broadcast_time > 10:
                self._broadcast_presence()
                self.last_broadcast_time = current_time
            
            # Обновляем статус
            self.status_var.set(f"Сеть: АКТИВНА | Пользователей: {len(self.peers)}")
            time.sleep(1)

    def _handle_network_message(self, ip, message):
        msg_type = message.get('type')
        
        if msg_type == 'presence':
            username = message['username']
            current_time = time.time()
            
            if ip not in self.user_join_times or current_time - self.user_join_times[ip] > 60:
                self._add_log("СИСТЕМА", f"Обнаружен пользователь: {username}", "network")
                self.user_join_times[ip] = current_time
            
            self.peers[ip] = {
                'username': username,
                'last_seen': current_time
            }
            self._update_user_list()
            
        elif msg_type == 'message':
            self._add_log(message['username'], message['text'], "message")
            # Помечаем для уведомления если окно не активно
            if not self._is_window_focused():
                self.pending_notification = True

    def _handle_incoming_call(self, conn, addr):
        if addr[0] in self.peers:
            username = self.peers[addr[0]]['username']
            
            # Создаем XP-style окно звонка
            call_window = tk.Toplevel(self.root)
            call_window.title("Входящий вызов")
            call_window.geometry("300x150")
            call_window.configure(bg='#d4d0c8')
            call_window.resizable(False, False)
            call_window.transient(self.root)
            
            # Центрируем
            call_window.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - call_window.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - call_window.winfo_height()) // 2
            call_window.geometry(f"+{x}+{y}")
            
            # Содержимое
            Label(call_window, text="📞 ВХОДЯЩИЙ ВЫЗОВ", bg='#d4d0c8',
                 font=('Tahoma', 11, 'bold')).pack(pady=(15, 5))
            
            Label(call_window, text=f"От: {username}", bg='#d4d0c8',
                 font=('Tahoma', 10), fg='blue').pack(pady=(0, 15))
            
            btn_frame = Frame(call_window, bg='#d4d0c8')
            btn_frame.pack()
            
            def accept_call():
                call_window.destroy()
                self.voice_socket = conn
                self.target_ip = addr[0]
                self.in_voice_chat = True
                self.call_start_time = time.time()
                
                if self._start_audio():
                    self._show_call_window()
                    self._update_ui_connected()
                    winsound.Beep(1000, 300)
                    
                    threading.Thread(target=self._voice_receive_loop, daemon=True).start()
                    threading.Thread(target=self._voice_send_loop, daemon=True).start()
                else:
                    conn.close()
            
            def reject_call():
                call_window.destroy()
                conn.close()
            
            Button(btn_frame, text="✅ Принять", command=accept_call, 
                  bg='#90ee90', font=('Tahoma', 9), width=10).pack(side='left', padx=10)
            Button(btn_frame, text="❌ Отклонить", command=reject_call,
                  bg='#ffcccb', font=('Tahoma', 9), width=10).pack(side='left', padx=10)

    def _show_call_window(self):
        """Окно активного звонка"""
        if self.call_window:
            self.call_window.destroy()
        
        self.call_window = tk.Toplevel(self.root)
        self.call_window.title("Активный звонок")
        self.call_window.geometry("250x120")
        self.call_window.configure(bg='#d4d0c8')
        self.call_window.resizable(False, False)
        
        # Центрируем
        self.call_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - self.call_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - self.call_window.winfo_height()) // 2
        self.call_window.geometry(f"+{x}+{y}")
        
        Label(self.call_window, text="📞 АКТИВНЫЙ ЗВОНОК", bg='#d4d0c8',
             font=('Tahoma', 10, 'bold')).pack(pady=10)
        
        username = self.peers[self.target_ip]['username']
        Label(self.call_window, text=f"С: {username}", bg='#d4d0c8',
             font=('Tahoma', 9)).pack()
        
        self.call_timer = Label(self.call_window, text="00:00", bg='#d4d0c8',
                              font=('Tahoma', 14, 'bold'), fg='green')
        self.call_timer.pack(pady=5)
        
        Button(self.call_window, text="Завершить", command=self._stop_call,
              bg='#ffcccb', font=('Tahoma', 8)).pack(pady=5)
        
        # Запускаем таймер
        self._update_call_timer()

    def _update_call_timer(self):
        if self.in_voice_chat and self.call_window:
            duration = int(time.time() - self.call_start_time)
            mins, secs = divmod(duration, 60)
            self.call_timer.config(text=f"{mins:02d}:{secs:02d}")
            self.call_window.after(1000, self._update_call_timer)

    def _start_audio(self):
        try:
            self._stop_audio()
            
            # Используем выбранные устройства или None для устройств по умолчанию
            self.stream_in = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.input_device_index
            )
            
            self.stream_out = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                output_device_index=self.output_device_index
            )
            
            self.recording = True
            self.playing = True
            return True
            
        except Exception as e:
            self._add_log("ОШИБКА", f"Ошибка запуска аудио: {e}", "error")
            return False

    def _stop_audio(self):
        self.recording = False
        self.playing = False
        
        if self.stream_in:
            try:
                self.stream_in.stop_stream()
                self.stream_in.close()
            except:
                pass
        
        if self.stream_out:
            try:
                self.stream_out.stop_stream()
                self.stream_out.close()
            except:
                pass

    def _voice_send_loop(self):
        while self.recording and self.voice_socket:
            try:
                data = self.stream_in.read(self.chunk_size, exception_on_overflow=False)
                if data and self.voice_socket:
                    self.voice_socket.sendall(data)
                
            except (socket.error, ConnectionError, OSError) as e:
                # Игнорируем ошибки разрыва соединения - это нормально при завершении звонка
                if not isinstance(e, (socket.error, ConnectionError)) or "10053" not in str(e) and "10054" not in str(e):
                    self._add_log("ОШИБКА", f"Ошибка отправки аудио: {e}", "error")
                break
            except Exception as e:
                self._add_log("ОШИБКА", f"Ошибка отправки аудио: {e}", "error")
                break
        self._stop_voice_chat()

    def _voice_receive_loop(self):
        while self.playing and self.voice_socket:
            try:
                data = self.voice_socket.recv(self.chunk_size)
                if data:
                    self.stream_out.write(data)
                
            except (socket.error, ConnectionError, OSError) as e:
                # Игнорируем ошибки разрыва соединения - это нормально при завершении звонка
                if not isinstance(e, (socket.error, ConnectionError)) or "10053" not in str(e) and "10054" not in str(e):
                    self._add_log("ОШИБКА", f"Ошибка приема аудио: {e}", "error")
                break
            except Exception as e:
                self._add_log("ОШИБКА", f"Ошибка приема аудио: {e}", "error")
                break
        self._stop_voice_chat()

    def _stop_voice_chat(self):
        if self.in_voice_chat:
            self.in_voice_chat = False
            self._stop_audio()
            
            if self.call_window:
                self.call_window.destroy()
                self.call_window = None
            
            if self.voice_socket:
                try:
                    self.voice_socket.close()
                except:
                    pass
                self.voice_socket = None
            
            self._update_ui_disconnected()
            winsound.Beep(600, 200)

    def _broadcast_presence(self):
        message = {
            'type': 'presence',
            'username': self.username,
            'timestamp': time.time()
        }
        data = json.dumps(message, ensure_ascii=False).encode('utf-8')
        
        try:
            self.udp_socket.sendto(data, ('255.255.255.255', self.udp_port))
        except:
            pass

    def _discover_peers(self):
        self._broadcast_presence()
        self._add_log("СИСТЕМА", "Сканирование сети...", "system")

    def _send_message(self, event=None):
        text = self.message_var.get().strip()
        if not text:
            return
        
        message = {
            'type': 'message',
            'username': self.username,
            'text': text,
            'timestamp': time.time()
        }
        data = json.dumps(message, ensure_ascii=False).encode('utf-8')
        
        sent = False
        for ip in self.peers:
            if ip != self.host_ip:
                try:
                    self.udp_socket.sendto(data, (ip, self.udp_port))
                    sent = True
                except:
                    pass
        
        if sent:
            self._add_log(f"{self.username} (Вы)", text, "self")
        else:
            self._add_log("СИСТЕМА", "Нет активных пользователей", "system")
        
        self.message_var.set("")

    def _start_call(self):
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя!")
            return
        
        selected = self.user_listbox.get(selection[0])
        target_ip = selected.split('(')[-1].rstrip(')')
        
        if target_ip == self.host_ip:
            messagebox.showwarning("Внимание", "Нельзя звонить самому себе!")
            return
        
        try:
            self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.voice_socket.settimeout(10)
            self.voice_socket.connect((target_ip, self.tcp_port))
            
            self.target_ip = target_ip
            self.in_voice_chat = True
            self.call_start_time = time.time()
            
            if self._start_audio():
                self._show_call_window()
                self._update_ui_connected()
                winsound.Beep(800, 200)
                
                threading.Thread(target=self._voice_receive_loop, daemon=True).start()
                threading.Thread(target=self._voice_send_loop, daemon=True).start()
            else:
                self.voice_socket.close()
                self.voice_socket = None
                
        except Exception as e:
            self._add_log("ОШИБКА", f"Ошибка соединения: {e}", "error")
            if self.voice_socket:
                self.voice_socket.close()
                self.voice_socket = None

    def _stop_call(self):
        self._stop_voice_chat()

    def _update_user_list(self):
        self.user_listbox.delete(0, 'end')
        # Добавляем себя в список
        self.user_listbox.insert('end', f"{self.username} (Вы) ({self.host_ip})")
        for ip, peer in self.peers.items():
            if ip != self.host_ip:
                self.user_listbox.insert('end', f"{peer['username']} ({ip})")

    def _update_ui_connected(self):
        self.call_btn.config(state='disabled')
        self.hangup_btn.config(state='normal')

    def _update_ui_disconnected(self):
        self.call_btn.config(state='normal')
        self.hangup_btn.config(state='disabled')

    def _add_log(self, sender, message, msg_type="system"):
        self.chat_text.config(state='normal')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        colors = {
            "system": "#004400",
            "error": "#880000",
            "network": "#000088",
            "voice": "#884400",
            "message": "#000000",
            "self": "#000080"
        }
        color = colors.get(msg_type, "#000000")
        
        if msg_type == "system":
            formatted_msg = f"[{timestamp}] СИСТЕМА: {message}\n"
        else:
            formatted_msg = f"[{timestamp}] {sender}: {message}\n"
        
        self.chat_text.insert('end', formatted_msg)
        self.chat_text.tag_add(msg_type, "end-2l", "end-1l")
        self.chat_text.tag_config(msg_type, foreground=color)
        
        self.chat_text.see('end')
        self.chat_text.config(state='disabled')

    def _show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки аудио")
        settings_window.geometry("450x400")
        settings_window.configure(bg='#d4d0c8')
        settings_window.resizable(False, False)
        
        Label(settings_window, text="⚙ НАСТРОЙКИ АУДИО", bg='#d4d0c8',
             font=('Tahoma', 11, 'bold')).pack(pady=10)
        
        # Создаем словари для соответствия индексов
        input_device_map = {}
        output_device_map = {}
        
        # Микрофон
        Label(settings_window, text="Микрофон:", bg='#d4d0c8',
             font=('Tahoma', 9)).pack(anchor='w', padx=20)
        
        input_var = tk.StringVar()
        input_combo = ttk.Combobox(settings_window, textvariable=input_var, 
                                 state='readonly', width=40, font=('Tahoma', 8))
        
        input_devices = ["По умолчанию"]
        input_device_map[0] = None
        
        current_input_index = 0
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    device_name = f"{info['name']} (ID: {i})"
                    input_devices.append(device_name)
                    index = len(input_devices) - 1
                    input_device_map[index] = i
                    if self.input_device_index == i:
                        current_input_index = index
            except:
                continue
        
        input_combo['values'] = input_devices
        input_combo.current(current_input_index)
        input_combo.pack(fill='x', padx=20, pady=5)
        
        # Тест микрофона
        def test_microphone():
            if self.mic_test_active:
                self.mic_test_active = False
                test_mic_btn.config(text="Тест микрофона")
            else:
                self.mic_test_active = True
                test_mic_btn.config(text="Остановить тест")
                threading.Thread(target=self._mic_test_thread, daemon=True).start()
        
        test_mic_btn = Button(settings_window, text="Тест микрофона", 
                            command=test_microphone, font=('Tahoma', 8))
        test_mic_btn.pack(anchor='w', padx=20, pady=5)
        
        # Динамики
        Label(settings_window, text="Динамики:", bg='#d4d0c8',
             font=('Tahoma', 9)).pack(anchor='w', padx=20)
        
        output_var = tk.StringVar()
        output_combo = ttk.Combobox(settings_window, textvariable=output_var, 
                                  state='readonly', width=40, font=('Tahoma', 8))
        
        output_devices = ["По умолчанию"]
        output_device_map[0] = None
        
        current_output_index = 0
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    device_name = f"{info['name']} (ID: {i})"
                    output_devices.append(device_name)
                    index = len(output_devices) - 1
                    output_device_map[index] = i
                    if self.output_device_index == i:
                        current_output_index = index
            except:
                continue
        
        output_combo['values'] = output_devices
        output_combo.current(current_output_index)
        output_combo.pack(fill='x', padx=20, pady=5)
        
        # Тест динамиков
        def test_speakers():
            try:
                frequency = 440
                duration = 0.3
                sample_rate = 44100
                
                samples = (np.sin(2 * np.pi * np.arange(sample_rate * duration) * frequency / sample_rate) * 32767).astype(np.int16)
                
                selected_index = output_combo.current()
                device_index = output_device_map.get(selected_index, None)
                
                stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    output=True,
                    output_device_index=device_index
                )
                stream.write(samples.tobytes())
                stream.stop_stream()
                stream.close()
            except Exception as e:
                self._add_log("ОШИБКА", f"Ошибка теста динамиков: {e}", "error")
        
        test_spk_btn = Button(settings_window, text="Тест динамиков", 
                            command=test_speakers, font=('Tahoma', 8))
        test_spk_btn.pack(anchor='w', padx=20, pady=5)
        
        # Громкость
        Label(settings_window, text="Громкость:", bg='#d4d0c8',
             font=('Tahoma', 9)).pack(anchor='w', padx=20)
        
        volume_scale = tk.Scale(settings_window, from_=0.0, to=1.0, resolution=0.1,
                              orient='horizontal', bg='#d4d0c8', length=300)
        volume_scale.set(self.volume)
        volume_scale.pack(padx=20, pady=10)
        
        def save_settings():
            input_index = input_combo.current()
            output_index = output_combo.current()
            
            self.input_device_index = input_device_map.get(input_index, None)
            self.output_device_index = output_device_map.get(output_index, None)
            self.volume = volume_scale.get()
            
            self._save_settings()
            settings_window.destroy()
            messagebox.showinfo("Настройки", "Настройки успешно сохранены!")
        
        # Кнопка сохранения настроек
        save_btn = Button(settings_window, text="💾 Сохранить", command=save_settings,
                        bg='#90ee90', font=('Tahoma', 9), width=15)
        save_btn.pack(pady=20)
        
        Button(settings_window, text="Закрыть", command=settings_window.destroy,
              bg='#d4d0c8', font=('Tahoma', 9), width=15).pack(pady=5)

    def _mic_test_thread(self):
        """Поток для тестирования микрофона с возможностью остановки"""
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=1024
            )
            
            output_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True,
                output_device_index=self.output_device_index,
                frames_per_buffer=1024
            )
            
            self._add_log("СИСТЕМА", "Тест микрофона запущен - вы слышите себя", "system")
            
            while self.mic_test_active:
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    output_stream.write(data)
                    time.sleep(0.01)
                except:
                    break
            
            stream.stop_stream()
            stream.close()
            output_stream.stop_stream()
            output_stream.close()
            
            self._add_log("СИСТЕМА", "Тест микрофона остановлен", "system")
            
        except Exception as e:
            self._add_log("ОШИБКА", f"Ошибка теста микрофона: {e}", "error")
            self.mic_test_active = False

    def _show_help(self):
        """Показываем справку в стиле XP"""
        help_text = """
GoidaPhone v1.7543 - Справка

📞 Голосовая связь:
- Выберите пользователя из списка
- Нажмите "ЗВОНОК" для начала разговора
- Нажмите "ЗАВЕРШИТЬ" для окончания

💬 Текстовые сообщения:
- Введите текст в поле ввода
- Нажмите Enter или кнопку "ОТПРАВИТЬ"

🌐 Сетевое соединение:
- Программа автоматически находит пользователей в локальной сети
- Для принудительного поиска нажмите "СКАНИРОВАТЬ"

⚙ Настройки аудио:
- Выберите устройства ввода/вывода в настройки
- Настройте громкость воспроизведения
- Тестируйте микрофон и динамики

🔊 Особенности:
- Уведомления Windows при новых сообщениях
- Стиль интерфейса Windows XP
- Стабильная работа в локальной сети

📞 О программе:
Версия: GoidaPhone v1.7543
Разработчик: Winora Company
Назначение: Локальная голосовая и текстовая связь
    """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("Справка GoidaPhone")
        help_window.geometry("500x450")
        help_window.configure(bg='#d4d0c8')
        help_window.resizable(False, False)
        
        # Заголовок
        header_frame = Frame(help_window, bg='#3a6ea5', relief='raised', bd=1)
        header_frame.pack(fill='x', pady=(0, 5))
        
        Label(header_frame, text="❓ СПРАВКА - GoidaPhone v1.7543", 
              bg='#3a6ea5', fg='white', font=('Tahoma', 10, 'bold'), pady=3).pack()
        
        # Текст справки
        text_frame = Frame(help_window, bg='#d4d0c8')
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap='word', 
                                              bg='white', fg='black',
                                              font=('Tahoma', 8),
                                              relief='sunken', bd=1)
        text_widget.pack(fill='both', expand=True)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')
        
        # Кнопка закрытия
        Button(help_window, text="Закрыть", command=help_window.destroy,
              bg='#d4d0c8', font=('Tahoma', 9), width=15).pack(pady=10)

    def _clear_chat(self):
        """Очищаем чат"""
        self.chat_text.config(state='normal')
        self.chat_text.delete(1.0, 'end')
        self.chat_text.config(state='disabled')
        self._add_log("СИСТЕМА", "Чат очищен", "system")

    def quit_app(self):
        """Корректный выход из приложения"""
        self._stop_call()
        self.mic_test_active = False
        self._save_settings()
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        if self.voice_listener:
            try:
                self.voice_listener.close()
            except:
                pass
        
        try:
            self.audio.terminate()
        except:
            pass
        
        self.root.quit()

def main():
    """Главная функция"""
    try:
        root = tk.Tk()
        app = GoidaPhone(root)
        
        def on_closing():
            app.quit_app()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Центрируем окно при запуске
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_width()) // 2
        y = (root.winfo_screenheight() - root.winfo_height()) // 2
        root.geometry(f"+{x}+{y}")
        
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Ошибка запуска", f"Не удалось запустить приложение:\n{str(e)}")

if __name__ == "__main__":
    main()