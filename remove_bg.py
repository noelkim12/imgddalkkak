#!/usr/bin/env python3
"""
이미지 배경 제거 도구 (Modern UI)
rembg 라이브러리를 사용하여 폴더 내 이미지들의 배경을 일괄 제거합니다.
드래그 앤 드롭, 이미지 리사이즈 기능 포함
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
# 드래그 앤 드롭 라이브러리 import (선택적)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    print("⚠️ tkinterdnd2가 설치되지 않음. 드래그 앤 드롭 기능 비활성화")
    DND_AVAILABLE = False
    # 기본 Tkinter 사용
    import tkinter as tk
    TkinterDnD = tk
from PIL import Image
import threading
from rembg import remove, new_session
import time
import json

class BackgroundRemover:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("이미지 딸깍툴")
        self.root.geometry("700x1115")
        self.root.resizable(True, True)
        self.root.minsize(650, 1115)
        
        # 모던 테마 색상
        self.colors = {
            'bg': '#f8f9fa',
            'card': '#ffffff',
            'primary': '#007bff',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'secondary': '#6c757d',
            'dark': '#343a40',
            'light': '#f8f9fa',
            'border': '#dee2e6',
            'text': '#495057',
            'muted': '#6c757d'
        }
        
        # 지원되는 이미지 확장자
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
        # 프로그램 종료 처리 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 배경 제거 탭 변수들
        self.folder_path = tk.StringVar()
        self.folder_queue = []  # 배경 제거용 폴더 대기열
        
        # 설정 변수들
        self.enable_resize = tk.BooleanVar(value=False)
        self.resize_width = tk.StringVar(value="1024")
        self.resize_height = tk.StringVar(value="768")
        self.maintain_aspect = tk.BooleanVar(value=True)
        
        # rembg 설정 변수들 (도트 픽셀 이미지에 최적화된 기본값)
        self.selected_model = tk.StringVar(value="u2netp")  # 도트 픽셀에 최적
        self.enable_alpha_matting = tk.BooleanVar(value=False)  # 도트 이미지에는 비추천
        self.alpha_matting_foreground_threshold = tk.StringVar(value="270")
        self.alpha_matting_background_threshold = tk.StringVar(value="10")
        self.alpha_matting_erode_size = tk.StringVar(value="10")
        
        # rembg 모델 정보
        self.model_options = {
            "u2net": "U²-Net (범용)",
            "u2net_human_seg": "U²-Net Human (사람 전용)",
            "u2netp": "U²-Net-P (도트픽셀 최적, 추천)",
            "silueta": "Silueta (고정밀)",
            "isnet-general-use": "ISNet (최신, 고성능)",
            "sam": "SAM (Segment Anything)",
            "birefnet-general": "BiRefNet (최고 품질)"
        }
        
        # 애니메이션 설정 변수들
        self.animation_folder_path = tk.StringVar()
        self.animation_queue = []  # 애니메이션용 폴더 대기열
        self.animation_format = tk.StringVar(value="webp")
        self.animation_duration = tk.StringVar(value="100")  # ms per frame
        self.animation_loop = tk.BooleanVar(value=True)
        self.animation_quality = tk.StringVar(value="80")
        self.prevent_ghosting = tk.BooleanVar(value=True)  # 잔상 방지
        
        # Alpha Matting 사용 가능 여부 체크
        self.alpha_matting_available = self.check_alpha_matting_availability()
        
        # Alpha Matting 설치 관련 사용자 선택 기억
        self.alpha_matting_install_declined = False
        
        self.setup_ui()
    
    def check_alpha_matting_availability(self):
        """Alpha Matting 라이브러리 사용 가능 여부 확인"""
        try:
            # alpha_matting_cutout 함수 import 테스트
            from rembg.bg import alpha_matting_cutout
            
            # 의존성 패키지들 확인
            try:
                import cv2
                import scipy
                import pymatting
                return True
            except ImportError:
                return False
        except ImportError:
            return False

    def setup_ui(self):
        """UI 구성"""
        # 메인 배경
        self.root.configure(bg=self.colors['bg'])
        
        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 제목 카드
        title_card = tk.Frame(main_container, bg=self.colors['card'], relief='flat', bd=0)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(
            title_card, 
            text="🖼️ 이미지 딸깍툴", 
            font=("맑은 고딕", 18, "bold"),
            bg=self.colors['card'],
            fg=self.colors['primary'],
            pady=20
        )
        title_label.pack()
        
        # 탭 컨테이너
        tab_container = tk.Frame(main_container, bg=self.colors['bg'])
        tab_container.pack(fill='both', expand=True)
        
        # 탭 노트북
        self.notebook = ttk.Notebook(tab_container)
        self.notebook.pack(fill='both', expand=True)
        
        # 배경 제거 탭
        self.bg_removal_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.bg_removal_frame, text="🗑️ 배경 제거")
        
        # 애니메이션 탭
        self.animation_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.animation_frame, text="🎬 애니메이션 생성")
        
        # 각 탭 내용 설정
        self.setup_bg_removal_tab()
        self.setup_animation_tab()
        
        # 초기 옵션 상태 설정
        self.toggle_resize_options()
        self.toggle_alpha_matting_options()
        
        # 프로그레스바 스타일 설정
        style = ttk.Style()
        style.configure('Custom.Horizontal.TProgressbar', background=self.colors['success'])
    
    def setup_bg_removal_tab(self):
        """배경 제거 탭 설정"""
        # 스크롤 가능한 프레임 생성
        canvas = tk.Canvas(self.bg_removal_frame, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.bg_removal_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 폴더 선택 카드
        folder_card = tk.Frame(scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        folder_card.pack(fill='x', pady=(10, 15), padx=10)
        
        # 폴더 선택 제목
        folder_title_frame = tk.Frame(folder_card, bg=self.colors['card'])
        folder_title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            folder_title_frame, 
            text="📁 처리할 폴더 (드래그 앤 드롭 또는 버튼 클릭)", 
            font=("맑은 고딕", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['dark']
        ).pack(anchor='w')
        
        # 드롭 존
        self.drop_frame = tk.Frame(
            folder_card, 
            bg=self.colors['light'], 
            relief='solid', 
            bd=2,
            height=80
        )
        self.drop_frame.pack(fill='x', padx=20, pady=(0, 15))
        self.drop_frame.pack_propagate(False)
        
        # 드롭 존 설정 (드래그 앤 드롭 라이브러리가 있을 때만)
        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        # 드롭 존 레이블
        drop_text = "📂 폴더를 여기에 드래그 하세요\n또는 아래 버튼을 클릭하세요" if DND_AVAILABLE else "📂 아래 버튼을 클릭해서 폴더를 선택하세요\n(드래그 앤 드롭: 비활성화)"
        self.drop_label = tk.Label(
            self.drop_frame,
            text=drop_text,
            font=("맑은 고딕", 10),
            bg=self.colors['light'],
            fg=self.colors['muted'],
            justify='center'
        )
        self.drop_label.pack(expand=True)
        
        # 폴더 경로 표시 및 선택 버튼
        folder_control_frame = tk.Frame(folder_card, bg=self.colors['card'])
        folder_control_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.folder_entry = tk.Entry(
            folder_control_frame, 
            textvariable=self.folder_path, 
            font=("맑은 고딕", 9),
            state='readonly',
            bg=self.colors['light'],
            relief='flat',
            bd=0
        )
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 10), ipady=8)
        
        folder_btn = tk.Button(
            folder_control_frame, 
            text="폴더 선택", 
            command=self.select_folder,
            bg=self.colors['secondary'],
            fg='white',
            font=("맑은 고딕", 9, "bold"),
            relief='flat',
            bd=0,
            padx=20,
            pady=8
        )
        folder_btn.pack(side='right')
        
        # 폴더 대기열 카드
        queue_card = tk.Frame(scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        queue_card.pack(fill='x', pady=(0, 15), padx=10)
        
        # 대기열 제목
        queue_title_frame = tk.Frame(queue_card, bg=self.colors['card'])
        queue_title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            queue_title_frame, 
            text="📋 처리 대기열", 
            font=("맑은 고딕", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['dark']
        ).pack(side='left')
        
        # 대기열 관리 버튼들
        queue_btn_frame = tk.Frame(queue_title_frame, bg=self.colors['card'])
        queue_btn_frame.pack(side='right')
        
        tk.Button(
            queue_btn_frame,
            text="➕ 추가",
            command=self.add_folder_to_queue,
            bg=self.colors['success'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left', padx=(0, 5))
        
        tk.Button(
            queue_btn_frame,
            text="➖ 제거",
            command=self.remove_folder_from_queue,
            bg=self.colors['danger'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left', padx=(0, 5))
        
        tk.Button(
            queue_btn_frame,
            text="🗑️ 전체 삭제",
            command=self.clear_folder_queue,
            bg=self.colors['secondary'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left')
        
        # 대기열 리스트
        queue_list_frame = tk.Frame(queue_card, bg=self.colors['card'])
        queue_list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.queue_listbox = tk.Listbox(
            queue_list_frame,
            height=6,
            font=("맑은 고딕", 9),
            bg=self.colors['light'],
            selectbackground=self.colors['primary'],
            selectforeground='white',
            relief='flat',
            bd=0
        )
        queue_scrollbar = tk.Scrollbar(queue_list_frame, command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        queue_scrollbar.pack(side='right', fill='y')
        
        # 리사이즈 설정 카드
        resize_card = tk.Frame(scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        resize_card.pack(fill='x', pady=(0, 15), padx=10)
        
        # 간단한 리사이즈 옵션
        resize_frame = tk.Frame(resize_card, bg=self.colors['card'])
        resize_frame.pack(fill='x', padx=20, pady=20)
        
        tk.Checkbutton(
            resize_frame,
            text="📏 리사이즈 사용",
            variable=self.enable_resize,
            font=("맑은 고딕", 10, "bold"),
            bg=self.colors['card'],
            fg=self.colors['primary']
        ).pack(side='left')
        
        tk.Label(resize_frame, text="크기:", bg=self.colors['card']).pack(side='left', padx=10)
        tk.Entry(resize_frame, textvariable=self.resize_width, width=8).pack(side='left', padx=2)
        tk.Label(resize_frame, text="x", bg=self.colors['card']).pack(side='left')
        tk.Entry(resize_frame, textvariable=self.resize_height, width=8).pack(side='left', padx=2)
        
        # rembg 설정 카드
        rembg_card = tk.Frame(scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        rembg_card.pack(fill='x', pady=(0, 15), padx=10)
        
        # rembg 제목
        rembg_title_frame = tk.Frame(rembg_card, bg=self.colors['card'])
        rembg_title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            rembg_title_frame, 
            text="🤖 AI 모델 및 배경 제거 설정", 
            font=("맑은 고딕", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['dark']
        ).pack(anchor='w')
        
        # 모델 선택
        model_frame = tk.Frame(rembg_card, bg=self.colors['card'])
        model_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Label(
            model_frame, 
            text="AI 모델:", 
            font=("맑은 고딕", 9, "bold"), 
            bg=self.colors['card'], 
            fg=self.colors['text']
        ).pack(anchor='w', pady=(0, 5))
        
        self.model_combo = ttk.Combobox(
            model_frame, 
            textvariable=self.selected_model,
            values=list(self.model_options.keys()),
            state='readonly',
            font=("맑은 고딕", 9),
            width=40
        )
        self.model_combo.pack(anchor='w', pady=(0, 5))
        self.model_combo.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # 모델 설명 레이블
        self.model_description = tk.Label(
            model_frame,
            text=self.model_options[self.selected_model.get()],
            font=("맑은 고딕", 8),
            bg=self.colors['card'],
            fg=self.colors['muted'],
            wraplength=500,
            justify='left'
        )
        self.model_description.pack(anchor='w', pady=(0, 10))
        
        # Alpha Matting 설정
        alpha_frame = tk.Frame(rembg_card, bg=self.colors['card'])
        alpha_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Alpha Matting 상태에 따른 텍스트 및 색상 설정
        if self.alpha_matting_available:
            alpha_text = "🎯 Alpha Matting 사용 (경계 개선, 처리시간 증가)"
            alpha_color = self.colors['primary']
            alpha_state = 'normal'
        else:
            alpha_text = "🎯 Alpha Matting (라이브러리 설치 필요 - 클릭 시 자동 설치)"
            alpha_color = self.colors['muted']
            alpha_state = 'normal'  # 클릭 가능하게 유지 (설치를 위해)
        
        alpha_toggle = tk.Checkbutton(
            alpha_frame,
            text=alpha_text,
            variable=self.enable_alpha_matting,
            command=self.toggle_alpha_matting_options,
            font=("맑은 고딕", 9, "bold"),
            bg=self.colors['card'],
            fg=alpha_color,
            selectcolor=self.colors['card'],
            activebackground=self.colors['card'],
            relief='flat',
            bd=0,
            state=alpha_state
        )
        alpha_toggle.pack(anchor='w', pady=(0, 10))
        
        # Alpha Matting 상세 설정
        self.alpha_options_frame = tk.Frame(alpha_frame, bg=self.colors['card'])
        self.alpha_options_frame.pack(fill='x', padx=20)
        
        # 임계값 설정들
        alpha_settings = [
            ("전경 임계값:", self.alpha_matting_foreground_threshold, "270", "전경 감지 민감도 (높을수록 정확)"),
            ("배경 임계값:", self.alpha_matting_background_threshold, "10", "배경 감지 민감도 (낮을수록 정확)"),
            ("침식 크기:", self.alpha_matting_erode_size, "10", "경계 부드러움 정도")
        ]
        
        for i, (label_text, var, default, desc) in enumerate(alpha_settings):
            setting_frame = tk.Frame(self.alpha_options_frame, bg=self.colors['card'])
            setting_frame.pack(fill='x', pady=2)
            
            tk.Label(
                setting_frame, 
                text=label_text, 
                font=("맑은 고딕", 8), 
                bg=self.colors['card'], 
                fg=self.colors['text'],
                width=12
            ).pack(side='left')
            
            entry = tk.Entry(
                setting_frame, 
                textvariable=var, 
                width=8,
                font=("맑은 고딕", 8), 
                relief='flat', 
                bd=1
            )
            entry.pack(side='left', padx=(5, 10))
            
            tk.Label(
                setting_frame, 
                text=desc, 
                font=("맑은 고딕", 8), 
                bg=self.colors['card'], 
                fg=self.colors['muted']
            ).pack(side='left')
        
        # 로그 및 진행률 카드
        log_card = tk.Frame(scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        log_card.pack(fill='both', expand=True, pady=(0, 15), padx=10)
        
        # 진행률
        progress_frame = tk.Frame(log_card, bg=self.colors['card'])
        progress_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(progress_frame, text="⏳ 진행률:", font=("맑은 고딕", 10, "bold"), 
                bg=self.colors['card']).pack(anchor='w')
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill='x', pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="대기 중...", 
                                     bg=self.colors['card'])
        self.progress_label.pack()
        
        # 로그
        tk.Label(log_card, text="📋 처리 로그:", font=("맑은 고딕", 10, "bold"), 
                bg=self.colors['card']).pack(anchor='w', padx=20)
        
        log_frame = tk.Frame(log_card, bg=self.colors['card'])
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.log_text = tk.Text(log_frame, height=6, bg=self.colors['light'])
        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # 버튼
        button_frame = tk.Frame(log_card, bg=self.colors['card'])
        button_frame.pack(pady=20)
        
        self.start_btn = tk.Button(
            button_frame,
            text="🚀 배경 제거 시작",
            command=self.start_processing,
            bg=self.colors['success'],
            fg='white',
            font=("맑은 고딕", 12, "bold"),
            padx=30,
            pady=10
        )
        self.start_btn.pack(side='left', padx=10)
        
        tk.Button(
            button_frame,
            text="❌ 종료",
            command=self.root.quit,
            bg=self.colors['danger'],
            fg='white',
            font=("맑은 고딕", 10),
            padx=20,
            pady=10
        ).pack(side='left', padx=10)
    
    def setup_animation_tab(self):
        """애니메이션 생성 탭 설정"""
        # 애니메이션 탭용 스크롤 프레임
        anim_canvas = tk.Canvas(self.animation_frame, bg=self.colors['bg'], highlightthickness=0)
        anim_scrollbar = ttk.Scrollbar(self.animation_frame, orient="vertical", command=anim_canvas.yview)
        anim_scrollable_frame = tk.Frame(anim_canvas, bg=self.colors['bg'])

        anim_scrollable_frame.bind(
            "<Configure>",
            lambda e: anim_canvas.configure(scrollregion=anim_canvas.bbox("all"))
        )

        anim_canvas.create_window((0, 0), window=anim_scrollable_frame, anchor="nw")
        anim_canvas.configure(yscrollcommand=anim_scrollbar.set)

        anim_canvas.pack(side="left", fill="both", expand=True)
        anim_scrollbar.pack(side="right", fill="y")
        
        # 애니메이션 폴더 선택 카드
        anim_folder_card = tk.Frame(anim_scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        anim_folder_card.pack(fill='x', pady=(10, 15), padx=10)
        
        # 폴더 선택 제목
        anim_folder_title_frame = tk.Frame(anim_folder_card, bg=self.colors['card'])
        anim_folder_title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            anim_folder_title_frame, 
            text="🎬 애니메이션용 이미지 폴더 선택", 
            font=("맑은 고딕", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['dark']
        ).pack(anchor='w')
        
        # 애니메이션 드롭 존
        self.anim_drop_frame = tk.Frame(
            anim_folder_card, 
            bg=self.colors['light'], 
            relief='solid', 
            bd=2,
            height=80
        )
        self.anim_drop_frame.pack(fill='x', padx=20, pady=(0, 15))
        self.anim_drop_frame.pack_propagate(False)
        
        # 드롭 존 설정
        if DND_AVAILABLE:
            self.anim_drop_frame.drop_target_register(DND_FILES)
            self.anim_drop_frame.dnd_bind('<<Drop>>', self.on_animation_drop)
        
        # 드롭 존 레이블
        anim_drop_text = "🎬 이미지 폴더를 드래그하세요\n또는 아래 버튼을 클릭하세요" if DND_AVAILABLE else "🎬 아래 버튼을 클릭해서 폴더를 선택하세요"
        self.anim_drop_label = tk.Label(
            self.anim_drop_frame,
            text=anim_drop_text,
            font=("맑은 고딕", 10),
            bg=self.colors['light'],
            fg=self.colors['muted'],
            justify='center'
        )
        self.anim_drop_label.pack(expand=True)
        
        # 애니메이션 폴더 경로 표시 및 선택 버튼
        anim_folder_control_frame = tk.Frame(anim_folder_card, bg=self.colors['card'])
        anim_folder_control_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.anim_folder_entry = tk.Entry(
            anim_folder_control_frame, 
            textvariable=self.animation_folder_path, 
            font=("맑은 고딕", 9),
            state='readonly',
            bg=self.colors['light'],
            relief='flat',
            bd=0
        )
        self.anim_folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 10), ipady=8)
        
        anim_folder_btn = tk.Button(
            anim_folder_control_frame, 
            text="폴더 선택", 
            command=self.select_animation_folder,
            bg=self.colors['secondary'],
            fg='white',
            font=("맑은 고딕", 9, "bold"),
            relief='flat',
            bd=0,
            padx=20,
            pady=8
        )
        anim_folder_btn.pack(side='right')
        
        # 애니메이션 폴더 대기열 카드
        anim_queue_card = tk.Frame(anim_scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        anim_queue_card.pack(fill='x', pady=(0, 15), padx=10)
        
        # 애니메이션 대기열 제목
        anim_queue_title_frame = tk.Frame(anim_queue_card, bg=self.colors['card'])
        anim_queue_title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            anim_queue_title_frame, 
            text="📋 애니메이션 처리 대기열", 
            font=("맑은 고딕", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['dark']
        ).pack(side='left')
        
        # 애니메이션 대기열 관리 버튼들
        anim_queue_btn_frame = tk.Frame(anim_queue_title_frame, bg=self.colors['card'])
        anim_queue_btn_frame.pack(side='right')
        
        tk.Button(
            anim_queue_btn_frame,
            text="➕ 추가",
            command=self.add_animation_folder_to_queue,
            bg=self.colors['success'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left', padx=(0, 5))
        
        tk.Button(
            anim_queue_btn_frame,
            text="➖ 제거",
            command=self.remove_animation_folder_from_queue,
            bg=self.colors['danger'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left', padx=(0, 5))
        
        tk.Button(
            anim_queue_btn_frame,
            text="🗑️ 전체 삭제",
            command=self.clear_animation_queue,
            bg=self.colors['secondary'],
            fg='white',
            font=("맑은 고딕", 8, "bold"),
            relief='flat',
            bd=0,
            padx=10,
            pady=5
        ).pack(side='left')
        
        # 애니메이션 대기열 리스트
        anim_queue_list_frame = tk.Frame(anim_queue_card, bg=self.colors['card'])
        anim_queue_list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.anim_queue_listbox = tk.Listbox(
            anim_queue_list_frame,
            height=6,
            font=("맑은 고딕", 9),
            bg=self.colors['light'],
            selectbackground=self.colors['primary'],
            selectforeground='white',
            relief='flat',
            bd=0
        )
        anim_queue_scrollbar = tk.Scrollbar(anim_queue_list_frame, command=self.anim_queue_listbox.yview)
        self.anim_queue_listbox.configure(yscrollcommand=anim_queue_scrollbar.set)
        
        self.anim_queue_listbox.pack(side='left', fill='both', expand=True)
        anim_queue_scrollbar.pack(side='right', fill='y')
        
        # 애니메이션 설정 카드
        anim_settings_card = tk.Frame(anim_scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        anim_settings_card.pack(fill='x', pady=(0, 15), padx=10)
        
        anim_settings_frame = tk.Frame(anim_settings_card, bg=self.colors['card'])
        anim_settings_frame.pack(fill='x', padx=20, pady=20)
        
        tk.Label(anim_settings_frame, text="⚙️ 애니메이션 설정", font=("맑은 고딕", 11, "bold"), 
                bg=self.colors['card'], fg=self.colors['dark']).pack(anchor='w', pady=(0, 10))
        
        # 설정 옵션들
        settings_row1 = tk.Frame(anim_settings_frame, bg=self.colors['card'])
        settings_row1.pack(fill='x', pady=5)
        
        tk.Label(settings_row1, text="형식:", bg=self.colors['card']).pack(side='left')
        format_combo = ttk.Combobox(
            settings_row1,
            textvariable=self.animation_format,
            values=["webp", "gif"],
            state='readonly',
            width=10
        )
        format_combo.pack(side='left', padx=10)
        
        tk.Label(settings_row1, text="프레임 지속시간(ms):", bg=self.colors['card']).pack(side='left', padx=(20, 5))
        tk.Entry(settings_row1, textvariable=self.animation_duration, width=8).pack(side='left', padx=5)
        
        settings_row2 = tk.Frame(anim_settings_frame, bg=self.colors['card'])
        settings_row2.pack(fill='x', pady=5)
        
        tk.Checkbutton(
            settings_row2,
            text="🔄 무한 반복",
            variable=self.animation_loop,
            bg=self.colors['card']
        ).pack(side='left')
        
        tk.Label(settings_row2, text="품질:", bg=self.colors['card']).pack(side='left', padx=(20, 5))
        tk.Entry(settings_row2, textvariable=self.animation_quality, width=8).pack(side='left', padx=5)
        tk.Label(settings_row2, text="(1-100)", bg=self.colors['card']).pack(side='left')
        
        # 잔상 방지 설정
        settings_row3 = tk.Frame(anim_settings_frame, bg=self.colors['card'])
        settings_row3.pack(fill='x', pady=5)
        
        tk.Checkbutton(
            settings_row3,
            text="🚫 잔상 방지 (권장)",
            variable=self.prevent_ghosting,
            bg=self.colors['card'],
            fg=self.colors['primary']
        ).pack(side='left')
        
        tk.Label(settings_row3, text="← 프레임 크기 통일 & disposal 설정", 
                bg=self.colors['card'], fg=self.colors['muted'], 
                font=("맑은 고딕", 8)).pack(side='left', padx=(10, 0))
        
        # 애니메이션 진행률 및 로그
        anim_log_card = tk.Frame(anim_scrollable_frame, bg=self.colors['card'], relief='flat', bd=0)
        anim_log_card.pack(fill='both', expand=True, pady=(0, 15), padx=10)
        
        # 진행률
        anim_progress_frame = tk.Frame(anim_log_card, bg=self.colors['card'])
        anim_progress_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(anim_progress_frame, text="⏳ 애니메이션 생성 진행률:", font=("맑은 고딕", 10, "bold"), 
                bg=self.colors['card']).pack(anchor='w')
        
        self.anim_progress = ttk.Progressbar(anim_progress_frame, mode='determinate')
        self.anim_progress.pack(fill='x', pady=5)
        
        self.anim_progress_label = tk.Label(anim_progress_frame, text="대기 중...", 
                                          bg=self.colors['card'])
        self.anim_progress_label.pack()
        
        # 로그
        tk.Label(anim_log_card, text="📋 애니메이션 생성 로그:", font=("맑은 고딕", 10, "bold"), 
                bg=self.colors['card']).pack(anchor='w', padx=20)
        
        anim_log_frame = tk.Frame(anim_log_card, bg=self.colors['card'])
        anim_log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.anim_log_text = tk.Text(anim_log_frame, height=6, bg=self.colors['light'])
        anim_log_scrollbar = tk.Scrollbar(anim_log_frame, command=self.anim_log_text.yview)
        self.anim_log_text.configure(yscrollcommand=anim_log_scrollbar.set)
        
        self.anim_log_text.pack(side='left', fill='both', expand=True)
        anim_log_scrollbar.pack(side='right', fill='y')
        
        # 버튼
        anim_button_frame = tk.Frame(anim_log_card, bg=self.colors['card'])
        anim_button_frame.pack(pady=20)
        
        self.create_animation_btn = tk.Button(
            anim_button_frame,
            text="🎬 애니메이션 생성",
            command=self.start_animation_creation,
            bg=self.colors['primary'],
            fg='white',
            font=("맑은 고딕", 12, "bold"),
            padx=30,
            pady=10
        )
        self.create_animation_btn.pack(side='left', padx=10)
    
    def on_animation_drop(self, event):
        """애니메이션용 드래그 앤 드롭 이벤트 처리 (다중 폴더 지원)"""
        if not DND_AVAILABLE:
            return
            
        files = self.root.tk.splitlist(event.data)
        if files:
            valid_folders = []
            invalid_items = []
            
            # 드래그된 모든 항목 확인
            for item in files:
                if os.path.isdir(item):
                    # 이미지 파일이 있는지 확인
                    image_files = self.get_image_files(item)
                    if image_files:
                        valid_folders.append(item)
                    else:
                        invalid_items.append(f"{os.path.basename(item)} (이미지 없음)")
                else:
                    invalid_items.append(f"{os.path.basename(item)} (파일)")
            
            # 유효한 폴더들을 순차적으로 애니메이션 대기열에 추가
            if valid_folders:
                added_count = 0
                for folder_path in valid_folders:
                    self.add_animation_folder_to_queue_internal(folder_path)
                    added_count += 1
                    image_files = self.get_image_files(folder_path)
                    self.anim_log_message(f"드래그 앤 드롭으로 애니메이션 대기열에 추가: {folder_path} ({len(image_files)}개 이미지)")
                
                # 첫 번째 폴더를 현재 선택된 폴더로 설정
                self.animation_folder_path.set(valid_folders[0])
                
                if len(valid_folders) == 1:
                    self.anim_drop_label.config(
                        text=f"✅ 선택된 폴더:\n{os.path.basename(valid_folders[0])}",
                        fg=self.colors['success']
                    )
                else:
                    self.anim_drop_label.config(
                        text=f"✅ {len(valid_folders)}개 폴더 대기열 추가:\n{os.path.basename(valid_folders[0])} 외 {len(valid_folders)-1}개",
                        fg=self.colors['success']
                    )
                
                self.anim_log_message(f"🎉 총 {added_count}개 폴더가 애니메이션 대기열에 추가되었습니다!")
            
            # 무효한 항목들이 있으면 경고
            if invalid_items:
                warning_msg = "다음 항목들은 처리할 수 없어 제외되었습니다:\n" + "\n".join(invalid_items)
                messagebox.showwarning("일부 항목 제외", warning_msg)
            
            # 유효한 폴더가 하나도 없으면 오류 메시지
            if not valid_folders:
                messagebox.showwarning("경고", "처리 가능한 이미지 폴더가 없습니다.")
    
    def select_animation_folder(self):
        """다중 애니메이션 폴더 선택 대화상자"""
        # 다중 폴더 선택을 위한 커스텀 대화상자 생성
        import tkinter as tk
        from tkinter import messagebox
        
        # 다중 폴더 선택 창 생성
        folder_window = tk.Toplevel(self.root)
        folder_window.title("애니메이션 폴더 선택")
        folder_window.geometry("600x400")
        folder_window.transient(self.root)
        folder_window.grab_set()
        
        # 선택된 폴더들을 저장할 리스트
        selected_folders = []
        
        # 상단 설명 라벨
        info_label = tk.Label(folder_window, text="여러 폴더를 선택하여 애니메이션 대기열에 추가할 수 있습니다", 
                             font=("Arial", 10), pady=10)
        info_label.pack()
        
        # 폴더 목록 표시 프레임
        list_frame = tk.Frame(folder_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 스크롤바가 있는 리스트박스
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        folder_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=folder_listbox.yview)
        
        def add_folder():
            folder = filedialog.askdirectory(title="추가할 애니메이션 폴더를 선택하세요")
            if folder and folder not in selected_folders:
                selected_folders.append(folder)
                folder_listbox.insert(tk.END, os.path.basename(folder) + f" ({folder})")
        
        def remove_folder():
            selection = folder_listbox.curselection()
            if selection:
                index = selection[0]
                selected_folders.pop(index)
                folder_listbox.delete(index)
        
        def confirm_selection():
            if not selected_folders:
                messagebox.showwarning("경고", "선택된 폴더가 없습니다.")
                return
            
            # 선택된 폴더들을 순차적으로 애니메이션 대기열에 추가
            added_count = 0
            for folder in selected_folders:
                if os.path.isdir(folder):
                    # 이미지 파일 확인
                    image_files = self.get_image_files(folder)
                    if image_files:
                        self.add_animation_folder_to_queue_internal(folder)
                        added_count += 1
                        self.anim_log_message(f"애니메이션 대기열에 추가: {folder} ({len(image_files)}개 이미지)")
                    else:
                        self.anim_log_message(f"⚠️ 이미지 파일이 없어 추가하지 않음: {folder}")
            
            if added_count > 0:
                self.anim_log_message(f"🎉 총 {added_count}개 폴더가 애니메이션 대기열에 추가되었습니다!")
                messagebox.showinfo("완료", f"{added_count}개 폴더가 애니메이션 대기열에 추가되었습니다.")
            
            folder_window.destroy()
        
        # 버튼 프레임
        button_frame = tk.Frame(folder_window)
        button_frame.pack(pady=10)
        
        add_btn = tk.Button(button_frame, text="➕ 폴더 추가", command=add_folder)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = tk.Button(button_frame, text="➖ 선택 제거", command=remove_folder)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        confirm_btn = tk.Button(button_frame, text="✅ 애니메이션 대기열에 추가", command=confirm_selection)
        confirm_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(button_frame, text="❌ 취소", command=folder_window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def anim_log_message(self, message):
        """애니메이션 로그 메시지 출력"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.anim_log_text.insert(tk.END, log_entry)
        self.anim_log_text.see(tk.END)
        self.root.update()
    
    def start_animation_creation(self):
        """애니메이션 생성 시작 (큐 처리)"""
        if not self.animation_queue:
            messagebox.showwarning("경고", "처리할 폴더 대기열이 비어있습니다. 폴더를 추가하세요.")
            return
        
        # UI 상태 변경
        self.create_animation_btn.config(state='disabled', text='⏳ 큐 생성 중...')
        self.anim_progress['value'] = 0
        self.anim_progress_label.config(text="애니메이션 큐 생성 중...")
        
        # 별도 스레드에서 처리 (UI 블로킹 방지)
        thread = threading.Thread(target=self.process_animation_queue)
        thread.daemon = True
        thread.start()
    
    def process_animation_queue(self):
        """애니메이션 폴더 대기열 처리"""
        try:
            total_folders = len(self.animation_queue)
            self.anim_log_message(f"🚀 총 {total_folders}개 폴더 애니메이션 큐 처리 시작")
            
            for folder_idx, folder_path in enumerate(self.animation_queue):
                self.anim_log_message(f"📁 [{folder_idx + 1}/{total_folders}] 애니메이션 생성 중: {os.path.basename(folder_path)}")
                
                # 전체 진행률 표시
                queue_progress = (folder_idx / total_folders) * 100
                self.anim_progress['value'] = queue_progress
                self.anim_progress_label.config(text=f"큐 생성 중... {folder_idx + 1}/{total_folders}")
                self.root.update()
                
                # 개별 폴더 애니메이션 생성
                self.create_single_animation(folder_path)
                
                self.anim_log_message(f"✅ [{folder_idx + 1}/{total_folders}] 완료: {os.path.basename(folder_path)}")
            
            # 완료
            self.anim_progress['value'] = 100
            self.anim_progress_label.config(text="큐 생성 완료")
            self.anim_log_message(f"🎉 모든 폴더 애니메이션 큐 생성 완료! (총 {total_folders}개)")
            
            # 완료 메시지
            messagebox.showinfo(
                "🎉 애니메이션 큐 생성 완료",
                f"모든 폴더의 애니메이션 생성이 완료되었습니다!\n\n"
                f"📊 생성된 애니메이션: {total_folders}개\n"
                f"📁 결과 저장 위치: animation/ 폴더"
            )
            
        except Exception as e:
            self.anim_log_message(f"❌ 애니메이션 큐 처리 오류: {str(e)}")
            messagebox.showerror("오류", f"애니메이션 큐 처리 중 오류가 발생했습니다:\n{str(e)}")
        
        finally:
            self.finish_animation_processing()
    
    def create_single_animation(self, folder_path_str):
        """단일 폴더 애니메이션 생성"""
        try:
            folder_path = Path(folder_path_str)
            
            # 이미지 파일 목록
            image_files = self.get_image_files(folder_path)
            
            if not image_files:
                self.anim_log_message("❌ 처리할 이미지 파일이 없습니다.")
                self.finish_animation_processing()
                return
            
            if len(image_files) < 2:
                self.anim_log_message("❌ 애니메이션을 만들려면 최소 2개 이상의 이미지가 필요합니다.")
                self.finish_animation_processing()
                return
            
            total_files = len(image_files)
            self.anim_log_message(f"🎬 총 {total_files}개 프레임으로 애니메이션 생성 시작")
            
            # 설정값 가져오기
            format_type = self.animation_format.get()
            duration = int(self.animation_duration.get())
            loop = self.animation_loop.get()
            quality = int(self.animation_quality.get())
            
            prevent_ghost = self.prevent_ghosting.get()
            self.anim_log_message(f"⚙️ 설정: {format_type.upper()}, {duration}ms/프레임, 무한반복: {'ON' if loop else 'OFF'}, 품질: {quality}")
            self.anim_log_message(f"🚫 잔상 방지: {'ON' if prevent_ghost else 'OFF'}")
            
            # 이미지 로드 및 전처리
            images = []
            max_width = 0
            max_height = 0
            
            # 1단계: 모든 이미지 로드 및 최대 크기 찾기
            temp_images = []
            for i, image_path in enumerate(image_files):
                try:
                    self.anim_log_message(f"📷 프레임 로딩: {image_path.name}")
                    
                    # 이미지 열기
                    img = Image.open(image_path)
                    
                    # RGBA로 변환 (투명도 지원)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    temp_images.append(img)
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
                    
                    # 진행률 업데이트 (로딩이 전체의 30%)
                    progress = (i + 1) / total_files * 30
                    self.anim_progress['value'] = progress
                    self.anim_progress_label.config(text=f"프레임 로딩 중... {i+1}/{total_files}")
                    self.root.update()
                    
                except Exception as e:
                    self.anim_log_message(f"❌ 프레임 로딩 실패 ({image_path.name}): {str(e)}")
            
            if not temp_images:
                self.anim_log_message("❌ 로드된 이미지가 없습니다.")
                return
            
            self.anim_log_message(f"📐 최대 크기: {max_width}x{max_height} (모든 프레임 통일)")
            
            # 2단계: 잔상 방지 설정에 따른 프레임 전처리
            if prevent_ghost:
                self.anim_log_message("🛠️ 잔상 방지 처리: 모든 프레임 크기 통일 중...")
                # 배치 처리로 최적화 (UI 업데이트 빈도 감소)
                batch_size = max(1, len(temp_images) // 10)  # 10회 정도만 업데이트
                for i, img in enumerate(temp_images):
                    try:
                        # 투명한 배경에 중앙 정렬로 배치
                        canvas = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))
                        
                        # 이미지를 캔버스 중앙에 배치
                        x_offset = (max_width - img.width) // 2
                        y_offset = (max_height - img.height) // 2
                        canvas.paste(img, (x_offset, y_offset), img)
                        
                        images.append(canvas)
                        
                        # 진행률 업데이트 (배치 처리로 UI 업데이트 빈도 감소)
                        if i % batch_size == 0 or i == len(temp_images) - 1:
                            progress = 30 + (i + 1) / len(temp_images) * 40
                            self.anim_progress['value'] = progress
                            self.anim_progress_label.config(text=f"잔상 방지 처리 중... {i+1}/{len(temp_images)}")
                            self.root.update()
                        
                    except Exception as e:
                        self.anim_log_message(f"❌ 프레임 전처리 실패: {str(e)}")
            else:
                # 잔상 방지 OFF: 원본 크기 유지
                self.anim_log_message("📐 원본 크기 유지 모드")
                images = temp_images
                for i in range(len(temp_images)):
                    progress = 30 + (i + 1) / len(temp_images) * 40
                    self.anim_progress['value'] = progress
                    self.anim_progress_label.config(text=f"프레임 준비 중... {i+1}/{len(temp_images)}")
                    self.root.update()
            
            if not images:
                self.anim_log_message("❌ 처리된 이미지가 없습니다.")
                return
            
            # 애니메이션 파일명 및 저장 경로 생성
            folder_name = folder_path.name  # 선택한 폴더명 추출
            
            # 스크립트와 같은 위치에 animation 폴더 생성
            script_dir = Path(__file__).parent
            output_base_folder = script_dir / "animation"
            output_base_folder.mkdir(exist_ok=True)
            
            # 중복된 파일명이 있을 경우 고유한 파일 경로 생성
            output_filename = f"{folder_name}.{format_type}"
            output_path = self.get_unique_file_path(output_base_folder, output_filename)
            
            if output_path.name != output_filename:
                self.anim_log_message(f"💾 애니메이션 저장 중 (중복으로 인한 이름 변경): {output_path.name}")
            else:
                self.anim_log_message(f"💾 애니메이션 저장 중: {output_filename}")
            
            # 애니메이션 생성 및 저장
            if format_type == "webp":
                webp_options = {
                    'save_all': True,
                    'append_images': images[1:],
                    'duration': duration,
                    'loop': 0 if loop else 1,
                    'lossless': False,
                    'quality': quality,
                    'method': 4  # 균형잡힌 압축 (6에서 4로 변경 - 더 빠름)
                }
                
                if prevent_ghost:
                    webp_options['disposal'] = 2  # 이전 프레임을 배경색으로 대체
                    self.anim_log_message("  🎯 WebP 설정: disposal=2 (잔상 방지)")
                else:
                    self.anim_log_message("  📐 WebP 설정: 기본 모드 (원본 크기 유지)")
                
                images[0].save(output_path, **webp_options)
                
            elif format_type == "gif":
                gif_options = {
                    'save_all': True,
                    'append_images': images[1:],
                    'duration': duration,
                    'loop': 0 if loop else 1,
                    'optimize': True
                }
                
                if prevent_ghost:
                    gif_options.update({
                        'disposal': 2,  # 이전 프레임을 배경색으로 대체
                        'transparency': 0,  # 투명도 활성화
                        'background': 0  # 배경 투명
                    })
                    self.anim_log_message("  🎯 GIF 설정: disposal=2, transparency=0 (잔상 방지)")
                else:
                    self.anim_log_message("  📐 GIF 설정: 기본 모드 (원본 크기 유지)")
                
                images[0].save(output_path, **gif_options)
            
            # 진행률 완료
            self.anim_progress['value'] = 100
            self.anim_progress_label.config(text="완료")
            
            self.anim_log_message(f"🎉 애니메이션 생성 완료!")
            self.anim_log_message(f"📁 저장 위치: {output_path}")
            
        except ValueError as e:
            self.anim_log_message(f"❌ 설정값 오류: {str(e)}")
        except Exception as e:
            folder_name = Path(folder_path_str).name
            self.anim_log_message(f"❌ 애니메이션 생성 오류 ({folder_name}): {str(e)}")
        
        # 이 메서드는 개별 폴더 처리이므로 finish_animation_processing 호출하지 않음
    
    def finish_animation_processing(self):
        """애니메이션 생성 완료 후 UI 상태 복원"""
        self.create_animation_btn.config(state='normal', text='🎬 애니메이션 생성')
        self.anim_progress_label.config(text="대기 중...")
    
    def on_drop(self, event):
        """드래그 앤 드롭 이벤트 처리 (다중 폴더 지원)"""
        if not DND_AVAILABLE:
            return
            
        files = self.root.tk.splitlist(event.data)
        if files:
            valid_folders = []
            invalid_items = []
            
            # 드래그된 모든 항목 확인
            for item in files:
                if os.path.isdir(item):
                    # 이미지 파일이 있는지 확인
                    image_files = self.get_image_files(item)
                    if image_files:
                        valid_folders.append(item)
                    else:
                        invalid_items.append(f"{os.path.basename(item)} (이미지 없음)")
                else:
                    invalid_items.append(f"{os.path.basename(item)} (파일)")
            
            # 유효한 폴더들을 순차적으로 대기열에 추가
            if valid_folders:
                added_count = 0
                for folder_path in valid_folders:
                    self.add_folder_to_queue_internal(folder_path)
                    added_count += 1
                    image_files = self.get_image_files(folder_path)
                    self.log_message(f"드래그 앤 드롭으로 대기열에 추가: {folder_path} ({len(image_files)}개 이미지)")
                
                # 첫 번째 폴더를 현재 선택된 폴더로 설정
                self.folder_path.set(valid_folders[0])
                
                if len(valid_folders) == 1:
                    self.drop_label.config(
                        text=f"✅ 선택된 폴더:\n{os.path.basename(valid_folders[0])}",
                        fg=self.colors['success']
                    )
                else:
                    self.drop_label.config(
                        text=f"✅ {len(valid_folders)}개 폴더 대기열 추가:\n{os.path.basename(valid_folders[0])} 외 {len(valid_folders)-1}개",
                        fg=self.colors['success']
                    )
                
                self.log_message(f"🎉 총 {added_count}개 폴더가 대기열에 추가되었습니다!")
            
            # 무효한 항목들이 있으면 경고
            if invalid_items:
                warning_msg = "다음 항목들은 처리할 수 없어 제외되었습니다:\n" + "\n".join(invalid_items)
                messagebox.showwarning("일부 항목 제외", warning_msg)
            
            # 유효한 폴더가 하나도 없으면 오류 메시지
            if not valid_folders:
                messagebox.showwarning("경고", "처리 가능한 이미지 폴더가 없습니다.")
    
    def add_folder_to_queue(self):
        """대기열에 폴더 추가 (버튼 클릭)"""
        folder = filedialog.askdirectory(title="대기열에 추가할 폴더를 선택하세요")
        if folder:
            self.add_folder_to_queue_internal(folder)
    
    def add_folder_to_queue_internal(self, folder_path):
        """대기열에 폴더 추가 (내부 호출)"""
        if folder_path not in self.folder_queue:
            self.folder_queue.append(folder_path)
            self.update_queue_display()
            self.log_message(f"📋 대기열에 추가: {os.path.basename(folder_path)}")
        else:
            self.log_message(f"⚠️ 이미 대기열에 있는 폴더: {os.path.basename(folder_path)}")
    
    def remove_folder_from_queue(self):
        """선택된 폴더를 대기열에서 제거"""
        selection = self.queue_listbox.curselection()
        if selection:
            index = selection[0]
            removed_folder = self.folder_queue.pop(index)
            self.update_queue_display()
            self.log_message(f"📋 대기열에서 제거: {os.path.basename(removed_folder)}")
        else:
            messagebox.showwarning("경고", "제거할 폴더를 선택하세요.")
    
    def clear_folder_queue(self):
        """대기열 전체 삭제"""
        if self.folder_queue:
            result = messagebox.askyesno("확인", f"대기열의 모든 폴더({len(self.folder_queue)}개)를 삭제하시겠습니까?")
            if result:
                self.folder_queue.clear()
                self.update_queue_display()
                self.log_message("📋 대기열이 모두 삭제되었습니다.")
        else:
            messagebox.showinfo("알림", "대기열이 이미 비어있습니다.")
    
    def update_queue_display(self):
        """대기열 표시 업데이트"""
        self.queue_listbox.delete(0, tk.END)
        for folder_path in self.folder_queue:
            display_text = f"{os.path.basename(folder_path)} ({len(self.get_image_files(folder_path))}개 이미지)"
            self.queue_listbox.insert(tk.END, display_text)
    
    def add_animation_folder_to_queue(self):
        """애니메이션 대기열에 폴더 추가 (버튼 클릭)"""
        folder = filedialog.askdirectory(title="애니메이션 대기열에 추가할 폴더를 선택하세요")
        if folder:
            self.add_animation_folder_to_queue_internal(folder)
    
    def add_animation_folder_to_queue_internal(self, folder_path):
        """애니메이션 대기열에 폴더 추가 (내부 호출)"""
        if folder_path not in self.animation_queue:
            self.animation_queue.append(folder_path)
            self.update_animation_queue_display()
            self.anim_log_message(f"📋 대기열에 추가: {os.path.basename(folder_path)}")
        else:
            self.anim_log_message(f"⚠️ 이미 대기열에 있는 폴더: {os.path.basename(folder_path)}")
    
    def remove_animation_folder_from_queue(self):
        """선택된 폴더를 애니메이션 대기열에서 제거"""
        selection = self.anim_queue_listbox.curselection()
        if selection:
            index = selection[0]
            removed_folder = self.animation_queue.pop(index)
            self.update_animation_queue_display()
            self.anim_log_message(f"📋 대기열에서 제거: {os.path.basename(removed_folder)}")
        else:
            messagebox.showwarning("경고", "제거할 폴더를 선택하세요.")
    
    def clear_animation_queue(self):
        """애니메이션 대기열 전체 삭제"""
        if self.animation_queue:
            result = messagebox.askyesno("확인", f"대기열의 모든 폴더({len(self.animation_queue)}개)를 삭제하시겠습니까?")
            if result:
                self.animation_queue.clear()
                self.update_animation_queue_display()
                self.anim_log_message("📋 대기열이 모두 삭제되었습니다.")
        else:
            messagebox.showinfo("알림", "대기열이 이미 비어있습니다.")
    
    def update_animation_queue_display(self):
        """애니메이션 대기열 표시 업데이트"""
        self.anim_queue_listbox.delete(0, tk.END)
        for folder_path in self.animation_queue:
            display_text = f"{os.path.basename(folder_path)} ({len(self.get_image_files(folder_path))}개 이미지)"
            self.anim_queue_listbox.insert(tk.END, display_text)
    
    def toggle_resize_options(self):
        """리사이즈 옵션 표시/숨김 토글"""
        # 현재는 항상 표시하므로 pass
        pass
    
    def toggle_alpha_matting_options(self):
        """Alpha Matting 옵션 표시/숨김 토글"""
        if self.enable_alpha_matting.get():
            # 옵션 활성화
            for widget in self.alpha_options_frame.winfo_children():
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, tk.Entry):
                            child.configure(state='normal')
                    except tk.TclError:
                        pass
        else:
            # 옵션 비활성화
            for widget in self.alpha_options_frame.winfo_children():
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, tk.Entry):
                            child.configure(state='disabled')
                    except tk.TclError:
                        pass
    
    def on_model_change(self, event=None):
        """모델 변경시 설명 업데이트"""
        selected_model = self.selected_model.get()
        description = self.model_options.get(selected_model, "")
        self.model_description.config(text=description)
        self.log_message(f"AI 모델 변경: {description}")
    
    def select_folder(self):
        """다중 폴더 선택 대화상자"""
        # 다중 폴더 선택을 위한 커스텀 대화상자 생성
        import tkinter as tk
        from tkinter import messagebox
        
        # 다중 폴더 선택 창 생성
        folder_window = tk.Toplevel(self.root)
        folder_window.title("폴더 선택")
        folder_window.geometry("600x400")
        folder_window.transient(self.root)
        folder_window.grab_set()
        
        # 선택된 폴더들을 저장할 리스트
        selected_folders = []
        
        # 상단 설명 라벨
        info_label = tk.Label(folder_window, text="여러 폴더를 선택하여 대기열에 추가할 수 있습니다", 
                             font=("Arial", 10), pady=10)
        info_label.pack()
        
        # 폴더 목록 표시 프레임
        list_frame = tk.Frame(folder_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 스크롤바가 있는 리스트박스
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        folder_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=folder_listbox.yview)
        
        def add_folder():
            folder = filedialog.askdirectory(title="추가할 폴더를 선택하세요")
            if folder and folder not in selected_folders:
                selected_folders.append(folder)
                folder_listbox.insert(tk.END, os.path.basename(folder) + f" ({folder})")
        
        def remove_folder():
            selection = folder_listbox.curselection()
            if selection:
                index = selection[0]
                selected_folders.pop(index)
                folder_listbox.delete(index)
        
        def confirm_selection():
            if not selected_folders:
                messagebox.showwarning("경고", "선택된 폴더가 없습니다.")
                return
            
            # 선택된 폴더들을 순차적으로 대기열에 추가
            added_count = 0
            for folder in selected_folders:
                if os.path.isdir(folder):
                    # 이미지 파일 확인
                    image_files = self.get_image_files(folder)
                    if image_files:
                        self.add_folder_to_queue_internal(folder)
                        added_count += 1
                        self.log_message(f"대기열에 추가: {folder} ({len(image_files)}개 이미지)")
                    else:
                        self.log_message(f"⚠️ 이미지 파일이 없어 추가하지 않음: {folder}")
            
            if added_count > 0:
                self.log_message(f"🎉 총 {added_count}개 폴더가 대기열에 추가되었습니다!")
                messagebox.showinfo("완료", f"{added_count}개 폴더가 대기열에 추가되었습니다.")
            
            folder_window.destroy()
        
        # 버튼 프레임
        button_frame = tk.Frame(folder_window)
        button_frame.pack(pady=10)
        
        add_btn = tk.Button(button_frame, text="➕ 폴더 추가", command=add_folder)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = tk.Button(button_frame, text="➖ 선택 제거", command=remove_folder)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        confirm_btn = tk.Button(button_frame, text="✅ 대기열에 추가", command=confirm_selection)
        confirm_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(button_frame, text="❌ 취소", command=folder_window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def get_image_files(self, folder_path):
        """폴더에서 지원되는 이미지 파일 목록 반환"""
        image_files = []
        folder = Path(folder_path)
        
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                image_files.append(file_path)
        
        return sorted(image_files)
    
    def get_unique_folder_path(self, base_folder, folder_name):
        """중복된 폴더명이 있을 경우 고유한 폴더 경로 반환"""
        unique_folder = base_folder / folder_name
        if not unique_folder.exists():
            return unique_folder
        
        counter = 2
        while True:
            unique_folder = base_folder / f"{folder_name}_{counter}"
            if not unique_folder.exists():
                return unique_folder
            counter += 1
    
    def get_unique_file_path(self, folder, filename):
        """중복된 파일명이 있을 경우 고유한 파일 경로 반환"""
        file_path = Path(filename)
        stem = file_path.stem
        suffix = file_path.suffix
        
        unique_file = folder / filename
        if not unique_file.exists():
            return unique_file
        
        counter = 2
        while True:
            unique_filename = f"{stem}_{counter}{suffix}"
            unique_file = folder / unique_filename
            if not unique_file.exists():
                return unique_file
            counter += 1
    
    def log_message(self, message):
        """로그 메시지 출력"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
    
    def start_processing(self):
        """배경 제거 처리 시작 (큐 처리)"""
        if not self.folder_queue:
            messagebox.showwarning("경고", "처리할 폴더 대기열이 비어있습니다. 폴더를 추가하세요.")
            return
        
        # UI 상태 변경
        self.start_btn.config(state='disabled', text='⏳ 큐 처리 중...')
        self.progress['value'] = 0
        self.progress_label.config(text="큐 처리 중...")
        
        # 별도 스레드에서 처리 (UI 블로킹 방지)
        thread = threading.Thread(target=self.process_queue)
        thread.daemon = True
        thread.start()
    
    def process_queue(self):
        """폴더 대기열 처리"""
        try:
            total_folders = len(self.folder_queue)
            self.log_message(f"🚀 총 {total_folders}개 폴더 큐 처리 시작")
            
            for folder_idx, folder_path in enumerate(self.folder_queue):
                self.log_message(f"📁 [{folder_idx + 1}/{total_folders}] 처리 중: {os.path.basename(folder_path)}")
                
                # 전체 진행률 표시
                queue_progress = (folder_idx / total_folders) * 100
                self.progress['value'] = queue_progress
                self.progress_label.config(text=f"큐 처리 중... {folder_idx + 1}/{total_folders}")
                self.root.update()
                
                # 개별 폴더 처리
                self.process_single_folder(folder_path)
                
                self.log_message(f"✅ [{folder_idx + 1}/{total_folders}] 완료: {os.path.basename(folder_path)}")
            
            # 완료
            self.progress['value'] = 100
            self.progress_label.config(text="큐 처리 완료")
            self.log_message(f"🎉 모든 폴더 큐 처리 완료! (총 {total_folders}개)")
            
            # 완료 메시지
            messagebox.showinfo(
                "🎉 큐 처리 완료",
                f"모든 폴더의 배경 제거가 완료되었습니다!\n\n"
                f"📊 처리된 폴더: {total_folders}개\n"
                f"📁 결과 저장 위치: transparent/ 폴더"
            )
            
        except Exception as e:
            self.log_message(f"❌ 큐 처리 오류: {str(e)}")
            messagebox.showerror("오류", f"큐 처리 중 오류가 발생했습니다:\n{str(e)}")
        
        finally:
            self.finish_processing()
    
    def create_rembg_session(self):
        """선택된 설정으로 rembg 세션 생성"""
        try:
            model_name = self.selected_model.get()
            self.log_message(f"🤖 AI 모델 로딩: {self.model_options[model_name]}")
            
            # 모델에 따른 세션 생성
            if model_name in ["u2net", "u2netp", "u2net_human_seg", "silueta", "isnet-general-use"]:
                session = new_session(model_name)
            else:
                # 기본값으로 fallback
                self.log_message(f"⚠️ 모델 '{model_name}' 지원되지 않음. u2net으로 변경")
                session = new_session("u2net")
            
            return session
        except Exception as e:
            self.log_message(f"❌ 모델 로딩 실패: {str(e)}")
            # 기본 모델로 fallback
            return new_session("u2net")
    
    def install_alpha_matting_dependencies(self):
        """Alpha Matting 의존성 자동 설치"""
        try:
            self.log_message("📦 Alpha Matting 라이브러리 설치 중...")
            self.log_message("  - pymatting (Alpha Matting 핵심)")
            self.log_message("  - opencv-python (이미지 처리)")
            self.log_message("  - scipy (수치 계산)")
            
            import subprocess
            import sys
            
            # 필요한 패키지들
            packages = [
                'pymatting',
                'opencv-python',
                'scipy'
            ]
            
            for package in packages:
                self.log_message(f"  📦 설치 중: {package}")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install', package, '--quiet'
                    ])
                    self.log_message(f"  ✅ 설치 완료: {package}")
                except subprocess.CalledProcessError as e:
                    self.log_message(f"  ❌ 설치 실패: {package} - {str(e)}")
                    return False
            
            self.log_message("🎉 Alpha Matting 라이브러리 설치 완료!")
            
            # 사용자에게 재시작 확인
            from tkinter import messagebox
            restart_choice = messagebox.askyesno(
                "설치 완료 - 재시작 필요",
                "Alpha Matting 라이브러리 설치가 완료되었습니다!\n\n"
                "변경사항을 적용하려면 프로그램을 재시작해야 합니다.\n\n"
                "지금 자동으로 재시작하시겠습니까?\n"
                "(아니요를 선택하면 수동으로 재시작해주세요)"
            )
            
            if restart_choice:
                self.log_message("  🔄 사용자 승인으로 프로그램 재시작 중...")
                # 카운트다운 시작
                self.restart_countdown = 3
                self.show_restart_countdown()
            else:
                self.log_message("  📋 수동 재시작 모드: 프로그램을 수동으로 재시작해주세요.")
                self.log_message("  💡 재시작 후 Alpha Matting 기능이 활성화됩니다!")
            
            return True
            
        except Exception as e:
            self.log_message(f"❌ Alpha Matting 라이브러리 설치 중 오류: {str(e)}")
            return False
    
    def show_restart_countdown(self):
        """재시작 카운트다운 표시"""
        if self.restart_countdown > 0:
            self.log_message(f"  ⏰ {self.restart_countdown}초 후 자동 재시작...")
            self.restart_countdown -= 1
            # 1초 후 다시 호출
            self.root.after(1000, self.show_restart_countdown)
        else:
            # 카운트다운 완료, 재시작 실행
            self.restart_application()
    
    def restart_application(self):
        """애플리케이션 재시작"""
        try:
            import sys
            import subprocess
            import os
            from pathlib import Path
            
            self.log_message("🔄 프로그램 재시작 중...")
            
            # 현재 스크립트가 있는 디렉토리
            script_dir = Path(__file__).parent
            
            # 재시작 방법 결정
            restart_bat = script_dir / "restart.bat"
            run_bat = script_dir / "run.bat"
            script_path = sys.argv[0]
            
            # 현재 프로그램 종료 예약
            self.root.after(1000, self.root.destroy)
            
            try:
                if restart_bat.exists():
                    # restart.bat 사용 (최우선)
                    subprocess.Popen([str(restart_bat)], 
                                   cwd=str(script_dir),
                                   creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                elif run_bat.exists():
                    # run.bat 사용 (차선책)
                    subprocess.Popen([str(run_bat)], 
                                   cwd=str(script_dir),
                                   creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                elif script_path.endswith('.py'):
                    # Python 직접 실행 (마지막 방법)
                    subprocess.Popen([sys.executable, script_path], 
                                   cwd=str(script_dir))
                else:
                    # 실행 파일인 경우
                    subprocess.Popen([script_path], 
                                   cwd=str(script_dir))
                    
                self.log_message("  ✅ 새 프로세스 시작 성공")
                
            except Exception as launch_error:
                self.log_message(f"  ❌ 재시작 실패: {str(launch_error)}")
                raise launch_error
                
        except Exception as e:
            self.log_message(f"❌ 재시작 중 오류 발생: {e}")
            # 재시작 실패 시 사용자에게 수동 재시작 안내
            from tkinter import messagebox
            messagebox.showinfo(
                "재시작 필요",
                "Alpha Matting 라이브러리 설치가 완료되었습니다.\n\n"
                "자동 재시작에 실패했습니다.\n"
                "프로그램을 수동으로 재시작해주세요.\n\n"
                f"오류: {str(e)}"
            )

    def process_with_rembg(self, input_data, session):
        """rembg를 사용하여 배경 제거 처리"""
        try:
            if self.enable_alpha_matting.get():
                # Alpha Matting 사용
                try:
                    from rembg.bg import alpha_matting_cutout
                    
                    # 임계값들 가져오기
                    fg_threshold = int(self.alpha_matting_foreground_threshold.get())
                    bg_threshold = int(self.alpha_matting_background_threshold.get())
                    erode_size = int(self.alpha_matting_erode_size.get())
                    
                    self.log_message(f"  🎯 Alpha Matting 적용 (FG:{fg_threshold}, BG:{bg_threshold}, Erode:{erode_size})")
                    
                    # 먼저 기본 rembg로 마스크 생성
                    from PIL import Image
                    import io
                    
                    # input_data를 PIL Image로 변환
                    input_image = Image.open(io.BytesIO(input_data))
                    
                    # RGB 모드로 변환 (RGBA나 다른 모드일 경우 대비)
                    if input_image.mode != 'RGB':
                        input_image = input_image.convert('RGB')
                    
                    # 기본 rembg로 마스크 생성
                    mask_data = remove(input_data, session=session)
                    mask_image = Image.open(io.BytesIO(mask_data))
                    
                    # 마스크에서 알파 채널만 추출 (RGBA -> L 모드)
                    if mask_image.mode == 'RGBA':
                        mask_image = mask_image.split()[-1]  # 알파 채널만 추출
                    elif mask_image.mode != 'L':
                        mask_image = mask_image.convert('L')  # 그레이스케일로 변환
                    
                    # trimap 생성 (Alpha Matting용)
                    import numpy as np
                    mask_array = np.array(mask_image)
                    
                    # 마스크 통계 확인
                    unique_values = np.unique(mask_array)
                    self.log_message(f"  📊 마스크 값 분포: min={mask_array.min()}, max={mask_array.max()}, unique={len(unique_values)}")
                    
                    # trimap 생성: 0(배경), 128(불확실), 255(전경)
                    trimap = np.zeros_like(mask_array, dtype=np.uint8)
                    
                    # 마스크 값을 0-1 범위로 정규화
                    mask_normalized = mask_array.astype(np.float32) / 255.0
                    fg_norm = fg_threshold / 255.0
                    bg_norm = bg_threshold / 255.0
                    
                    # 높은 값(전경) 영역을 255로 설정
                    trimap[mask_normalized > fg_norm] = 255  # 확실한 전경
                    
                    # 낮은 값(배경) 영역을 0으로 설정  
                    trimap[mask_normalized < bg_norm] = 0    # 확실한 배경
                    
                    # 중간 값은 128로 설정 (불확실한 영역)
                    trimap[(mask_normalized >= bg_norm) & (mask_normalized <= fg_norm)] = 128
                    
                    # trimap 통계 확인
                    fg_count = np.sum(trimap == 255)
                    bg_count = np.sum(trimap == 0)
                    uncertain_count = np.sum(trimap == 128)
                    
                    self.log_message(f"  🎯 Trimap - 전경: {fg_count}, 배경: {bg_count}, 불확실: {uncertain_count}")
                    
                    # 전경이 없으면 임계값 조정
                    if fg_count == 0:
                        self.log_message(f"  ⚠️ 전경 영역이 없음. 임계값을 자동 조정합니다.")
                        # 마스크의 상위 20% 값을 전경으로 설정
                        fg_auto_threshold = np.percentile(mask_array[mask_array > 0], 80)
                        fg_auto_norm = fg_auto_threshold / 255.0
                        trimap[mask_normalized > fg_auto_norm] = 255
                        fg_count = np.sum(trimap == 255)
                        self.log_message(f"  🔧 자동 조정된 전경 임계값: {fg_auto_threshold:.1f} (정규화: {fg_auto_norm:.3f}), 전경 픽셀: {fg_count}")
                    
                    # PIL Image로 변환
                    trimap_image = Image.fromarray(trimap, mode='L')
                    
                    self.log_message(f"  🔍 원본: {input_image.mode} {input_image.size}, Trimap: {trimap_image.mode} {trimap_image.size}")
                    
                    # Alpha Matting으로 경계 개선 (정규화된 임계값 사용)
                    result_image = alpha_matting_cutout(
                        input_image,
                        trimap_image,
                        fg_norm,  # 0-1 범위 정규화된 값 사용
                        bg_norm,  # 0-1 범위 정규화된 값 사용
                        erode_size
                    )
                    
                    # 결과를 bytes로 변환
                    output_buffer = io.BytesIO()
                    result_image.save(output_buffer, format='PNG')
                    output_data = output_buffer.getvalue()
                    
                except ImportError as e:
                    self.log_message(f"  ⚠️ Alpha Matting 라이브러리 없음: {str(e)}")
                    
                    # 이미 사용자가 설치를 거부했다면 묻지 않음
                    if not self.alpha_matting_install_declined:
                        # 사용자에게 설치 여부 확인
                        from tkinter import messagebox
                        install_choice = messagebox.askyesno(
                            "Alpha Matting 라이브러리 필요",
                            "Alpha Matting을 사용하려면 추가 라이브러리가 필요합니다.\n\n"
                            "필요한 패키지:\n"
                            "- pymatting (Alpha Matting 핵심)\n"
                            "- opencv-python (이미지 처리)\n" 
                            "- scipy (수치 계산)\n\n"
                            "지금 자동으로 설치하시겠습니까?\n"
                            "(인터넷 연결이 필요하며, 시간이 걸릴 수 있습니다)"
                        )
                        
                        if not install_choice:
                            # 사용자가 설치를 거부했음을 기억
                            self.alpha_matting_install_declined = True
                            self.log_message("  📋 Alpha Matting 설치가 취소되었습니다. 기본 배경 제거를 사용합니다.")
                            
                    if not self.alpha_matting_install_declined and 'install_choice' in locals() and install_choice:
                        # 설치 시도
                        install_success = self.install_alpha_matting_dependencies()
                        if install_success:
                            # 설치 성공 시 현재 처리는 기본 모드로 하고 재시작 예정
                            self.log_message("  📋 현재 처리는 기본 모드를 사용합니다.")
                            self.log_message("  🚀 재시작 후 Alpha Matting이 활성화됩니다!")
                            
                            # 현재 처리 중단 방지를 위해 기본 처리로 진행
                            output_data = remove(input_data, session=session)
                            return output_data  # 재시작 전에 현재 작업 완료
                        else:
                            self.log_message("  ❌ 설치 실패. 기본 처리를 사용합니다.")
                    
                    # 설치가 취소되었거나 이미 거부된 경우 기본 처리
                    output_data = remove(input_data, session=session)
                    
                except ValueError as e:
                    self.log_message(f"  ⚠️ Alpha Matting 설정 오류: {str(e)}. 기본 처리 사용")
                    output_data = remove(input_data, session=session)
                except Exception as e:
                    self.log_message(f"  ❌ Alpha Matting 처리 오류: {str(e)}. 기본 처리 사용")
                    output_data = remove(input_data, session=session)
            else:
                # 기본 rembg 처리
                output_data = remove(input_data, session=session)
            
            return output_data
        except Exception as e:
            self.log_message(f"  ❌ 배경 제거 실패: {str(e)}")
            raise

    def resize_image(self, image):
        """이미지 리사이즈 처리"""
        if not self.enable_resize.get():
            return image
        
        try:
            target_width = int(self.resize_width.get())
            target_height = int(self.resize_height.get())
            
            if self.maintain_aspect.get():
                # 비율 유지하며 리사이즈
                image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            else:
                # 강제 리사이즈
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
            return image
        except ValueError:
            self.log_message("오류: 올바른 크기 값을 입력해주세요")
            return image
        except Exception as e:
            self.log_message(f"리사이즈 오류: {str(e)}")
            return image

    def process_single_folder(self, folder_path_str):
        """단일 폴더 이미지 처리"""
        try:
            folder_path = Path(folder_path_str)
            folder_name = folder_path.name  # 선택한 폴더명 추출
            
            # 스크립트와 같은 위치에 transparent 폴더 생성
            script_dir = Path(__file__).parent
            output_base_folder = script_dir / "transparent"
            output_base_folder.mkdir(exist_ok=True)
            
            # 중복된 폴더명이 있을 경우 고유한 폴더 경로 생성
            output_folder = self.get_unique_folder_path(output_base_folder, folder_name)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            if output_folder.name != folder_name:
                self.log_message(f"📁 출력 폴더 생성 (중복으로 인한 이름 변경): {output_folder}")
            else:
                self.log_message(f"📁 출력 폴더 생성: {output_folder}")
            
            # 이미지 파일 목록
            image_files = self.get_image_files(folder_path)
            
            if not image_files:
                self.log_message("❌ 처리할 이미지 파일이 없습니다.")
                self.finish_processing()
                return
            
            # rembg 세션 생성 (한 번만 생성하여 성능 향상)
            session = self.create_rembg_session()
            
            total_files = len(image_files)
            processed = 0
            success_count = 0
            
            # 처리 설정 정보 로그
            self.log_message(f"🚀 총 {total_files}개 파일 처리 시작")
            self.log_message(f"🤖 사용 모델: {self.model_options[self.selected_model.get()]}")
            if self.enable_alpha_matting.get():
                self.log_message(f"🎯 Alpha Matting: 활성화")
            if self.enable_resize.get():
                self.log_message(f"📏 리사이즈: {self.resize_width.get()}x{self.resize_height.get()}" + 
                               (" (비율유지)" if self.maintain_aspect.get() else " (강제변경)"))
            
            for image_path in image_files:
                try:
                    self.log_message(f"🖼️ 처리 중: {image_path.name}")
                    
                    # 원본 이미지 읽기
                    with open(image_path, 'rb') as input_file:
                        input_data = input_file.read()
                    
                    # 선택된 설정으로 배경 제거
                    output_data = self.process_with_rembg(input_data, session)
                    
                    # 리사이즈가 활성화된 경우 처리
                    if self.enable_resize.get():
                        # PIL Image로 변환
                        from io import BytesIO
                        image = Image.open(BytesIO(output_data))
                        
                        # 원본 크기 로그
                        original_size = image.size
                        self.log_message(f"  원본 크기: {original_size[0]}x{original_size[1]}")
                        
                        # 리사이즈 적용
                        resized_image = self.resize_image(image)
                        new_size = resized_image.size
                        self.log_message(f"  리사이즈 후: {new_size[0]}x{new_size[1]}")
                        
                        # 다시 바이트로 변환
                        output_io = BytesIO()
                        resized_image.save(output_io, format='PNG', optimize=True)
                        output_data = output_io.getvalue()
                    
                    # 결과 저장 (PNG 형식으로 저장하여 투명도 유지)
                    output_filename = image_path.stem + '.png'
                    output_path = self.get_unique_file_path(output_folder, output_filename)
                    
                    with open(output_path, 'wb') as output_file:
                        output_file.write(output_data)
                    
                    if output_path.name != output_filename:
                        self.log_message(f"✅ 저장 완료 (중복으로 인한 이름 변경): {output_path.name}")
                    else:
                        self.log_message(f"✅ 저장 완료: {output_filename}")
                    
                    success_count += 1
                    
                except Exception as e:
                    self.log_message(f"❌ 오류 ({image_path.name}): {str(e)}")
                
                processed += 1
                
                # 진행률 업데이트
                progress_percent = (processed / total_files) * 100
                self.progress['value'] = progress_percent
                self.progress_label.config(text=f"{processed}/{total_files} 완료")
                self.root.update()
            
            self.log_message(f"\n🎉 처리 완료!")
            self.log_message(f"✅ 성공: {success_count}개, ❌ 실패: {total_files - success_count}개")
            self.log_message(f"🤖 사용 모델: {self.model_options[self.selected_model.get()]}")
            if self.enable_alpha_matting.get():
                self.log_message(f"🎯 Alpha Matting: 사용됨")
            if self.enable_resize.get():
                self.log_message(f"📏 리사이즈: {self.resize_width.get()}x{self.resize_height.get()}" + 
                               (" (비율유지)" if self.maintain_aspect.get() else " (강제변경)"))
            self.log_message(f"📁 결과 저장 위치: {output_folder}")
            
            # 완료 메시지
            model_info = f"\n🤖 모델: {self.model_options[self.selected_model.get()]}"
            alpha_info = f"\n🎯 Alpha Matting: {'사용' if self.enable_alpha_matting.get() else '미사용'}"
            resize_info = ""
            if self.enable_resize.get():
                resize_info = f"\n📏 리사이즈: {self.resize_width.get()}x{self.resize_height.get()}" + \
                             (" (비율유지)" if self.maintain_aspect.get() else " (강제변경)")
            
            messagebox.showinfo(
                "🎉 처리 완료", 
                f"이미지 처리가 완료되었습니다!\n"
                f"✅ 성공: {success_count}개\n"
                f"❌ 실패: {total_files - success_count}개"
                f"{model_info}{alpha_info}{resize_info}\n\n"
                f"📁 저장 위치:\n{output_folder}"
            )
            
        except Exception as e:
            self.log_message(f"전체 처리 오류: {str(e)}")
            messagebox.showerror("오류", f"처리 중 오류가 발생했습니다:\n{str(e)}")
        
        except Exception as e:
            self.log_message(f"❌ 폴더 처리 오류 ({folder_name}): {str(e)}")
        
        # 이 메서드는 개별 폴더 처리이므로 finish_processing 호출하지 않음
    
    def finish_processing(self):
        """처리 완료 후 UI 상태 복원"""
        self.start_btn.config(state='normal', text='🚀 배경 제거 시작')
        self.progress_label.config(text="완료")
    
    def on_closing(self):
        """GUI 창 닫힘 처리"""
        try:
            # 진행 중인 작업이 있는지 확인 (배경 제거 또는 애니메이션 생성)
            bg_processing = hasattr(self, 'start_btn') and self.start_btn.cget('state') == 'disabled'
            anim_processing = hasattr(self, 'create_animation_btn') and self.create_animation_btn.cget('state') == 'disabled'
            
            if bg_processing or anim_processing:
                # 작업 진행 중일 때 확인 대화상자
                from tkinter import messagebox
                if messagebox.askokcancel("종료 확인", 
                    "작업이 진행 중입니다. 정말 종료하시겠습니까?\n진행 중인 작업이 중단될 수 있습니다."):
                    self.log_message("사용자에 의한 프로그램 종료")
                    self.root.quit()  # 이벤트 루프 종료
                    self.root.destroy()  # 창 닫기
                else:
                    return  # 취소 시 종료하지 않음
            else:
                # 일반적인 종료
                self.log_message("프로그램 정상 종료")
                self.root.quit()  # 이벤트 루프 종료
                self.root.destroy()  # 창 닫기
        except Exception as e:
            # 오류 발생 시에도 확실히 종료
            print(f"종료 처리 중 오류: {e}")
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """애플리케이션 실행"""
        self.root.mainloop()

def main():
    """메인 함수"""
    try:
        app = BackgroundRemover()
        app.run()
    except Exception as e:
        print(f"애플리케이션 실행 오류: {e}")
        input("Enter 키를 눌러 종료하세요...")

if __name__ == "__main__":
    main()