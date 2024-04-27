# 导入Python标准库和第三方库中定义的模块
import collections  # 用于处理如列表、字典等集合类型的高级操作
import darkdetect  # 用于检测当前系统的主题是浅色还是深色，以便于应用程序可以适配
import os  # 用于处理文件和目录
import sys  # 用于访问与Python解释器相关的变量和函数
import time  # 用于时间相关的操作
import threading  # 用于多线程操作
import tkinter as tk  # 用于创建图形用户界面
import webbrowser  # 用于在默认浏览器中打开网页
from PIL import Image  # Python Imaging Library，用于图像处理
from PIL import ImageTk  # 用于在Tkinter中显示PIL图像
from tkinter import filedialog  # 用于创建打开文件和保存文件的对话框
from tkinter import messagebox  # 用于创建消息框
from tkinter import ttk  # 用于创建主题化的小部件
from tkinter.scrolledtext import ScrolledText  # 用于创建带有滚动条的文本框
from tkinterdnd2 import DND_FILES, TkinterDnD  # 用于实现Tkinter的拖放功能

# 导入项目特定的模块
import param  # 项目特定的参数配置模块
import task  # 项目特定的任务处理模块

# 根据是否有_MEIPASS属性来确定基础路径，_MEIPASS通常在使用PyInstaller打包时设置
BASE_PATH = sys._MEIPASS if hasattr(sys, '_MEIPASS') else ''
# 获取应用程序的路径
APP_PATH = os.path.dirname(os.path.realpath(sys.executable if hasattr(sys, '_MEIPASS') else __file__))

# 导入构建时间，这个值在构建应用程序时被设置
from build_time import BUILD_TIME

class REGUIApp(ttk.Frame):  # 创建一个基于ttk.Frame的类
    def __init__(self, parent: tk.Tk):  # 类的初始化方法
        super().__init__(parent)  # 调用父类的初始化方法
        # 获取模型目录中的文件，并筛选出有效的模型文件
        modelFiles = set(os.listdir(os.path.join(APP_PATH, 'models')))
        self.models = sorted(
            x for x in set(os.path.splitext(y)[0] for y in modelFiles)
            if f'{x}.bin' in modelFiles and f'{x}.param' in modelFiles
        )
        # 将特定的模型插入到模型列表的前面
        for m in (
            'realesrgan-x4plus',
            'realesrgan-x4plus-anime',
        )[::-1]:
            try:
                self.models.insert(0, self.models.pop(self.models.index(m)))
            except ValueError:
                pass
        # 创建一个字典来存储每个模型的倍数因子
        self.modelFactors: dict[str, int] = {}
        for m in self.models:
            self.modelFactors[m] = 4
            for i in range(2, 5):
                if f'x{i}' in m:
                    self.modelFactors[m] = i
                    break

        # 设置下采样方法
        self.downsample = (
            ('Lanczos', Image.Resampling.LANCZOS),
            ('Bicubic', Image.Resampling.BICUBIC),
            ('Hamming', Image.Resampling.HAMMING),
            ('Bilinear', Image.Resampling.BILINEAR),
            ('Box', Image.Resampling.BOX),
            ('Nearest', Image.Resampling.NEAREST),
        )
        # 设置分块大小选项
        self.tileSize = (0, 32, 64, 128, 256, 512, 1024)

        # 调用方法来设置应用程序的变量
        self.setupVars()
        # 调用方法来设置应用程序的控件
        self.setupWidgets()

    def setupVars(self):
        # 创建Tkinter字符串变量，用于在控件间共享数据
        self.varstrInputPath = tk.StringVar()
        self.varstrOutputPath = tk.StringVar()
        # 创建Tkinter整数变量，用于存储尺寸计算方式
        self.varintResizeMode = tk.IntVar(value=int(param.ResizeMode.RATIO))
        self.varintResizeRatio = tk.IntVar(value=4)
        self.varintResizeWidth = tk.IntVar()
        self.varintResizeHeight = tk.IntVar()
        # 创建Tkinter字符串变量，用于存储选择的模型
        self.varstrModel = tk.StringVar()
        # 创建Tkinter整数变量，用于存储下采样方式和分块大小的索引
        self.varintDownsampleIndex = tk.IntVar()
        self.varintTileSizeIndex = tk.IntVar()
        self.varintGPUID = tk.IntVar()
        # 创建Tkinter布尔变量，用于存储是否使用TTA模式和WebP格式
        self.varboolUseTTA = tk.BooleanVar()
        self.varboolUseWebP = tk.BooleanVar()

    def setupWidgets(self):
        # 配置窗口的行和列，设置权重使窗口可以按比例分配空间
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # 创建一个Notebook控件，用于在不同选项卡间切换
        self.notebookConfig = ttk.Notebook(self)
        self.notebookConfig.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)

        # 创建基本配置的Frame
        self.frameBasicConfig = ttk.Frame(self.notebookConfig, padding=5)
        self.frameBasicConfig.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)

        # 在基本配置Frame中添加输入路径的标签
        ttk.Label(self.frameBasicConfig, text='输入（文件或文件夹）').pack(padx=10, pady=5, fill=tk.X)

        # 创建包含输入路径Entry和浏览按钮的Frame
        self.frameInputPath = ttk.Frame(self.frameBasicConfig)
        self.frameInputPath.columnconfigure(0, weight=1)  # 设置列的权重
        self.frameInputPath.columnconfigure(1, weight=0)
        self.frameInputPath.pack(padx=5, pady=5, fill=tk.X)  # 将Frame填充到其父容器

        # 创建输入路径的Entry控件，使用前面创建的字符串变量
        self.entryInputPath = ttk.Entry(self.frameInputPath, textvariable=self.varstrInputPath)
        self.entryInputPath.grid(row=0, column=0, padx=5, sticky=tk.EW)  # 将Entry放置在Frame中

        # 创建浏览按钮，点击时会调用buttonInputPath_click方法
        self.buttonInputPath = ttk.Button(self.frameInputPath, text='浏览', command=self.buttonInputPath_click)
        self.buttonInputPath.grid(row=0, column=1, padx=5)  # 将按钮放置在Frame中

        # 在基本配置Frame中添加输出路径的标签
        ttk.Label(self.frameBasicConfig, text='输出').pack(padx=10, pady=5, fill=tk.X)

        # 创建包含输出路径Entry和浏览按钮的Frame
        self.frameOutputPath = ttk.Frame(self.frameBasicConfig)
        self.frameOutputPath.columnconfigure(0, weight=1)  # 设置列的权重
        self.frameOutputPath.columnconfigure(1, weight=0)
        self.frameOutputPath.pack(padx=5, pady=5, fill=tk.X)  # 将Frame填充到其父容器

        # 创建输出路径的Entry控件，使用前面创建的字符串变量
        self.entryOutputPath = ttk.Entry(self.frameOutputPath, textvariable=self.varstrOutputPath)
        self.entryOutputPath.grid(row=0, column=0, padx=5, sticky=tk.EW)  # 将Entry放置在Frame中
        # 创建一个输出路径浏览按钮，并将其放置在输出路径输入框旁边
        self.buttonOutputPath = ttk.Button(self.frameOutputPath, text='浏览', command=self.buttonOutputPath_click)
        # 将按钮放置在其父Frame中，占据第0行和第1列，设置填充和粘附属性
        self.buttonOutputPath.grid(row=0, column=1, padx=5)

        # 创建一个底部的Frame，用于放置模型选择器和尺寸调整控件
        self.frameBasicConfigBottom = ttk.Frame(self.frameBasicConfig)
        # 配置列的权重，使子控件可以按比例分配空间
        self.frameBasicConfigBottom.columnconfigure(0, weight=0)
        self.frameBasicConfigBottom.columnconfigure(1, weight=1)
        # 将底部Frame放置在基本配置Frame中，填满X方向
        self.frameBasicConfigBottom.pack(fill=tk.X)

        # 创建一个模型选择器的Frame，并将其放置在底部Frame的第0行第1列
        self.frameModel = ttk.Frame(self.frameBasicConfigBottom)
        self.frameModel.grid(row=0, column=1, sticky=tk.NSEW)
        # 添加一个标签，说明这是一个模型选择器
        ttk.Label(self.frameModel, text='模型').pack(padx=10, pady=5, fill=tk.X)
        # 创建一个下拉菜单，用于选择不同的模型
        self.comboModel = ttk.Combobox(self.frameModel, state='readonly', values=self.models,
                                       textvariable=self.varstrModel)
        # 默认选择第一个模型
        self.comboModel.current(0)
        # 将模型下拉菜单放置在模型选择器Frame中
        self.comboModel.pack(padx=10, pady=5, fill=tk.X)
        # 绑定下拉菜单的选择事件，当选择改变时清除当前选择
        self.comboModel.bind('<<ComboboxSelected>>', lambda e: e.widget.select_clear())

        # 创建预览标签
        self.labelPreview = ttk.Label(self.frameModel, text='预览')
        self.labelPreview.pack(side=tk.LEFT, padx=10, pady=5)

        # 创建一个用于显示图片的Frame
        self.imageDisplayFrame = ttk.Frame(self.frameModel, width=150, height=150)  # 根据需要设置宽度和高度
        self.imageDisplayFrame.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.BOTH, expand=True)      #紧贴上一个frame,更美观 算了不折腾了 pack和gird

        # 假设您有一个方法用于加载并显示图片
        # self.load_and_display_preview_image()

        # 绑定下拉菜单的选择事件，当选择改变时调用您的load_and_display_image方法
        # self.comboModel.bind('<<ComboboxSelected>>', self.load_and_display_preview_image())

        # 创建一个尺寸调整控件的Frame，并将其放置在底部Frame的第0行第0列
        self.frameResize = ttk.Frame(self.frameBasicConfigBottom)
        self.frameResize.grid(row=0, column=0, sticky=tk.NSEW)
        # 添加一个标签，说明这是一个尺寸调整控件
        ttk.Label(self.frameResize, text='放大尺寸计算方式').grid(row=0, column=0, columnspan=2, padx=10, pady=5,
                                                                  sticky=tk.EW)
        # 创建固定倍率的单选按钮，并将其放置在第1行第0列
        self.radioResizeRatio = ttk.Radiobutton(self.frameResize, text='固定倍率', value=int(param.ResizeMode.RATIO),
                                                variable=self.varintResizeMode)
        self.radioResizeRatio.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
        # 创建一个输入框，用于设置固定倍率的值，并将其放置在第1行第1列
        self.spinResizeRatio = ttk.Spinbox(self.frameResize, from_=2, to=16, increment=1, width=12,
                                           textvariable=self.varintResizeRatio)
        self.spinResizeRatio.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        # 创建等比放大到宽度的单选按钮，并将其放置在第2行第0列
        self.radioResizeWidth = ttk.Radiobutton(self.frameResize, text='等比放大到宽度',
                                                value=int(param.ResizeMode.WIDTH), variable=self.varintResizeMode)
        self.radioResizeWidth.grid(row=2, column=0, padx=5, pady=5, sticky=tk.EW)
        # 创建一个输入框，用于设置等比放大到宽度的值，并将其放置在第2行第1列
        self.spinResizeWidth = ttk.Spinbox(self.frameResize, from_=1, to=16383, increment=1, width=12,
                                           textvariable=self.varintResizeWidth)
        self.spinResizeWidth.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        # 创建等比放大到高度的单选按钮，并将其放置在第3行第0列
        self.radioResizeHeight = ttk.Radiobutton(self.frameResize, text='等比放大到高度',
                                                 value=int(param.ResizeMode.HEIGHT), variable=self.varintResizeMode)
        self.radioResizeHeight.grid(row=3, column=0, padx=5, pady=5, sticky=tk.EW)
        # 创建一个输入框，用于设置等比放大到高度的值，并将其放置在第3行第1列
        self.spinResizeHeight = ttk.Spinbox(self.frameResize, from_=1, to=16383, increment=1, width=12,
                                            textvariable=self.varintResizeHeight)
        self.spinResizeHeight.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)

        # 创建一个开始处理按钮，并将其放置在底部Frame的第0行第1列
        self.buttonProcess = ttk.Button(self.frameBasicConfigBottom, text='开始', style='Accent.TButton', width=6,
                                        command=self.buttonProcess_click)
        self.buttonProcess.grid(row=0, column=1, padx=5, pady=5, sticky=tk.SE)

        # 创建一个高级配置的Frame，并将其放置在Notebook的第0行第0列
        self.frameAdvancedConfig = ttk.Frame(self.notebookConfig, padding=5)
        self.frameAdvancedConfig.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        # 配置列的权重，使子控件可以按比例分配空间
        self.frameAdvancedConfig.columnconfigure(0, weight=1)
        self.frameAdvancedConfig.columnconfigure(1, weight=1)

        # 创建高级配置左侧的Frame，并将其放置在高级配置Frame的第0行第0列
        self.frameAdvancedConfigLeft = ttk.Frame(self.frameAdvancedConfig)
        self.frameAdvancedConfigLeft.grid(row=0, column=0, sticky=tk.NSEW)
        # 创建高级配置右侧的Frame，并将其放置在高级配置Frame的第0行第1列
        self.frameAdvancedConfigRight = ttk.Frame(self.frameAdvancedConfig)
        self.frameAdvancedConfigRight.grid(row=0, column=1, sticky=tk.NSEW)

        # 在高级配置左侧Frame中添加降采样方式的标签
        ttk.Label(self.frameAdvancedConfigLeft, text='降采样方式').pack(padx=10, pady=5, fill=tk.X)
        # 创建一个下拉菜单，用于选择不同的降采样方式，并将其放置在高级配置左侧Frame中
        self.comboDownsample = ttk.Combobox(self.frameAdvancedConfigLeft, state='readonly',
                                            values=tuple(x[0] for x in self.downsample))
        self.comboDownsample.current(0)
        self.comboDownsample.pack(padx=10, pady=5, fill=tk.X)
        # 绑定下拉菜单的选择事件，当选择改变时执行comboDownsample_click方法
        self.comboDownsample.bind('<<ComboboxSelected>>', self.comboDownsample_click)

        # 在高级配置左侧Frame中添加使用的 GPU ID 的标签
        ttk.Label(self.frameAdvancedConfigLeft, text='使用的 GPU ID').pack(padx=10, pady=5, fill=tk.X)
        # 创建一个输入框，用于设置使用的 GPU ID，并将其放置在高级配置左侧Frame中
        self.spinGPUID = ttk.Spinbox(self.frameAdvancedConfigLeft, from_=0, to=7, increment=1, width=12,
                                     textvariable=self.varintGPUID)
        self.spinGPUID.set(0)
        self.spinGPUID.pack(padx=10, pady=5, fill=tk.X)

        # 在高级配置左侧Frame中添加拆分大小的标签
        ttk.Label(self.frameAdvancedConfigLeft, text='拆分大小').pack(padx=10, pady=5, fill=tk.X)
        # 创建一个下拉菜单，用于选择不同的拆分大小，并将其放置在高级配置左侧Frame中
        self.comboTileSize = ttk.Combobox(self.frameAdvancedConfigLeft, state='readonly',
                                          values=('自动决定', *self.tileSize[1:]))
        self.comboTileSize.current(0)
        self.comboTileSize.pack(padx=10, pady=5, fill=tk.X)
        # 绑定下拉菜单的选择事件，当选择改变时执行comboTileSize_click方法
        self.comboTileSize.bind('<<ComboboxSelected>>', self.comboTileSize_click)

        # 在高级配置右侧Frame中添加优先保存为无损 WebP 的复选框
        self.checkUseWebP = ttk.Checkbutton(self.frameAdvancedConfigRight, text='优先保存为无损 WebP',
                                            style='Switch.TCheckbutton', variable=self.varboolUseWebP)
        self.checkUseWebP.pack(padx=10, pady=5, fill=tk.X)

        # 在高级配置右侧Frame中添加使用 TTA 模式的复选框
        self.checkUseTTA = ttk.Checkbutton(self.frameAdvancedConfigRight,
                                           text='使用 TTA 模式（速度大幅下降，稍微提高质量）', style='Switch.TCheckbutton',
                                           variable=self.varboolUseTTA)
        # 将使用TTA模式的复选框放置在高级配置右侧Frame中
        self.checkUseTTA.pack(padx=10, pady=5, fill=tk.X)

        # # 创建关于页面的Frame，并将其放置在Notebook的第0行第0列
        # self.frameAbout = ttk.Frame(self.notebookConfig, padding=5)
        # self.frameAbout.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        #
        # # 设置关于页面的内容，包括图标、应用程序名称和构建信息
        # self.frameAboutContent = ttk.Frame(self.frameAbout)
        # self.frameAboutContent.place(relx=.5, rely=.5, anchor=tk.CENTER)  # 将Frame放置在父容器的中心
        #
        # # 设置字体大小
        # f = ttk.Label().cget('font').string.split(' ')
        # f[-1] = '16'
        # f = ' '.join(f)
        #
        # # 将应用程序图标添加到关于页面
        # self.imageIcon = ImageTk.PhotoImage(Image.open(os.path.join(BASE_PATH, 'icon-128px.webp')))
        # ttk.Label(self.frameAboutContent, image=self.imageIcon).pack(padx=10, pady=10)
        #
        # # 添加应用程序名称到关于页面
        # ttk.Label(self.frameAboutContent, text='Real-ESRGAN GUI', font=f, justify=tk.CENTER).pack()
        # ttk.Label(self.frameAboutContent, text='By TransparentLC' + (time.strftime("\nBuilt at %Y-%m-%d %H:%M:%S", time.localtime(BUILD_TIME)) if BUILD_TIME else ""), justify=tk.CENTER).pack()
        # self.frameAboutBottom = ttk.Frame(self.frameAboutContent)
        # self.frameAboutBottom.pack()
        #
        # # 创建查看源代码的按钮，并将其放置在关于页面底部的Frame中
        # # ttk.Button(self.frameAboutBottom, text='查看源代码', command=lambda: webbrowser.open_new_tab('https://github.com/TransparentLC/realesrgan-gui')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        #
        # # 创建查看Real-ESRGAN介绍的按钮，并将其放置在关于页面底部的Frame中
        # ttk.Button(self.frameAboutBottom, text='查看 Real-ESRGAN 介绍', command=lambda: webbrowser.open_new_tab('https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan')).grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)

        # 将基本设定、高级设定和关于页面添加到Notebook控件
        self.notebookConfig.add(self.frameBasicConfig, text='基本设置')
        self.notebookConfig.add(self.frameAdvancedConfig, text='高级设置')
        # self.notebookConfig.add(self.frameAbout, text='关于')

        # 创建一个滚动文本框，用于显示处理过程的输出信息
        self.textOutput = ScrolledText(self)
        self.textOutput.grid(row=1, column=0, padx=5, pady=5, sticky=tk.NSEW)
        # 初始时禁用文本框，防止用户编辑
        self.textOutput.configure(state=tk.DISABLED)

    # 预览图片加载和显示方法
    def load_and_display_preview_image(self, p:str):
        # # 清除Frame中的旧图片
        # for widget in self.imageDisplayFrame.winfo_children():
        #     widget.destroy()
        # 根据当前选择的模型加载新的图片
        # 这里只是一个示例，您需要根据实际情况来加载图片
        # current_model = self.varstrModel.get()

        # 使用Pillow加载图片
        pil_image = Image.open(p)
        # 获取原始图片的尺寸
        original_width, original_height = pil_image.size

        # 计算等比例缩放的尺寸，高度不超过300像素
        aspect_ratio = original_width / original_height
        if original_height > 300:
            resized_height = 300
            resized_width = int(300 * aspect_ratio)
        else:
            resized_height = original_height
            resized_width = original_width

        # 调整图片尺寸
        pil_image = pil_image.resize((resized_width, resized_height))

        # 将Pillow图像转换为Tkinter的PhotoImage        后者只能支持png图片
        tk_image = ImageTk.PhotoImage(pil_image)

        # 更新self.imageDisplayFrame的大小以适应图片
        self.imageDisplayFrame.config(width=resized_width, height=resized_height)

        # 创建一个新的Label并将其打包到imageDisplayFrame中
        #ttk.Label(self.imageDisplayFrame, image=tk_image).pack(side=tk.TOP, fill=tk.BOTH, expand=True)    #这行单独出现时不显示，和下面类似代码出现时却重复显示图片，猜测不显示是因为tk_image是局部变量，函数执行完就销毁了

        # 更新窗口大小以适应图片Frame的新尺寸
        self.update_window_size()

        self.image = tk_image   #可能是局部变量问题
        # ttk.Label(self.imageDisplayFrame, image=self.image).pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        ttk.Label(self.imageDisplayFrame, image=self.image).pack(side=tk.TOP, fill=tk.BOTH, expand=True)      #踏马的到底是什么问题突然显示又突然不显示,大概率是要在update_win 后面执行

        #其实不显示图片的原因大概率是解释器还没来得及加载新代码(py没有编译器)

    def update_window_size(self):
        # 获取self.imageDisplayFrame的当前宽度和高度
        width = self.imageDisplayFrame.cget('width')
        height = self.imageDisplayFrame.cget('height')

        # 确保文本框至少有250像素的高度
        minimum_height = max(250, height)

        # 设置窗口的最小尺寸
        root.minsize(width, minimum_height)

        # 更新窗口大小
        root.geometry(f'{720+width}x{540+minimum_height}')
    # 当用户点击按钮选择输入路径时调用此函数
    def buttonInputPath_click(self):
        # 弹出文件选择对话框，只显示图片文件类型
        p = filedialog.askopenfilename(filetypes=(
            ('Image files', ('.jpg', '.png', '.gif', '.webp')),
        ))
        # 如果用户没有选择文件，即p为空，则函数结束
        if not p:
            return
        # 用户选择了文件，将其路径设置为输入路径
        self.setInputPath(p)
        self.load_and_display_preview_image(p)

    # 当用户点击按钮选择输出路径时调用此函数
    def buttonOutputPath_click(self):
        # 弹出文件选择对话框，只显示图片文件类型
        p = filedialog.askopenfilename(filetypes=(
            ('Image files', ('.png', '.gif', '.webp')),
        ))
        # 如果用户没有选择文件，即p为空，则函数结束
        if not p:
            return
        # 用户选择了文件，将其路径设置为输出路径
        self.varstrOutputPath.set(p)

    # 当用户点击下拉菜单选择下采样选项时调用此函数
    def comboDownsample_click(self, event: tk.Event):
        # 清除当前选中的下采样选项
        self.comboDownsample.select_clear()
        # 获取当前下采样选项的索引，并设置到相应的变量中
        self.varintDownsampleIndex.set(self.comboDownsample.current())

    # 当用户点击下拉菜单选择平铺尺寸选项时调用此函数
    def comboTileSize_click(self, event: tk.Event):
        # 清除当前选中的平铺尺寸选项
        self.comboTileSize.select_clear()
        # 获取当前平铺尺寸选项的索引，并设置到相应的变量中
        self.varintTileSizeIndex.set(self.comboTileSize.current())

    # 当用户点击处理按钮时调用此函数
    def buttonProcess_click(self):
        # 获取输入和输出路径
        inputPath = self.varstrInputPath.get()
        outputPath = self.varstrOutputPath.get()
        # 如果输入或输出路径为空，则通过弹出警告框提示用户并结束函数
        if not inputPath or not outputPath:
            return messagebox.showwarning(None, '请输入有效的输入和输出路径。')
        # 规范化路径格式
        inputPath = os.path.normpath(inputPath)
        outputPath = os.path.normpath(outputPath)
        # 如果输入路径不存在，则通过弹出警告框提示用户并结束函数
        if not os.path.exists(inputPath):
            return messagebox.showwarning(None, '输入的文件或目录不存在。')

        # 获取配置参数
        initialConfigParams = self.getConfigParams()
        # 创建一个队列用于存放处理任务
        queue = collections.deque()
        # 如果输入路径是一个目录，则遍历目录中的所有文件
        if os.path.isdir(inputPath):
            # 对于每个文件，如果文件扩展名不在支持的图片格式中，则跳过
            for curDir, dirs, files in os.walk(inputPath):
                for f in files:
                    if os.path.splitext(f)[1].lower() not in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
                        continue
                    # 构造完整的文件路径
                    f = os.path.join(curDir, f)
                    # 构造输出文件的路径
                    g = os.path.join(outputPath, f.removeprefix(inputPath + os.path.sep))
                    # 根据文件类型添加处理任务到队列
                    queue.append((
                        task.SplitGIFTask(self.writeToOutput, f, g, initialConfigParams, queue)
                        if os.path.splitext(f)[1].lower() == '.gif' else
                        task.RESpawnTask(self.writeToOutput, f, g, initialConfigParams)
                    ))
            # 如果队列为空，即没有可以处理的图片文件，则通过弹出警告框提示用户
            if not queue:
                return messagebox.showwarning('批量处理提示', '文件夹内没有可以处理的图片文件。')
        # 如果输入路径是一个文件，并且是支持的图片格式，则添加处理任务到队列
        elif os.path.splitext(inputPath)[1].lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
            queue.append((
                task.SplitGIFTask(self.writeToOutput, inputPath, outputPath, initialConfigParams, queue)
                if os.path.splitext(inputPath)[1].lower() == '.gif' else
                task.RESpawnTask(self.writeToOutput, inputPath, outputPath, initialConfigParams)
            ))
        else:
            # 如果输入文件格式不支持，则通过弹出警告框提示用户
            return messagebox.showwarning('格式错误', '仅支持 JPEG、PNG、GIF 和 WebP 格式的图片文件。')
        # 禁用处理按钮
        self.buttonProcess.config(state=tk.DISABLED)
        # 使文本框可编辑，清除文本框内容，然后再次禁用
        self.textOutput.config(state=tk.NORMAL)
        self.textOutput.delete(1.0, tk.END)
        self.textOutput.config(state=tk.DISABLED)
        # 创建并启动新线程来执行任务队列
        t = threading.Thread(
            target=task.taskRunner,
            args=(
                queue,
                self.writeToOutput,
                lambda: self.buttonProcess.config(state=tk.NORMAL),
            )
        )
        t.start()

    # 设置输入文件路径的函数
    def setInputPath(self, p: str):
        # 设置输入路径变量的值为用户选择的路径
        self.varstrInputPath.set(p)
        # 根据输入路径设置默认的输出路径
        self.varstrOutputPath.set(self.getOutputPath(p))

    # 将处理结果写入文本输出框的函数
    def writeToOutput(self, s: str):
        # 使文本框可编辑
        self.textOutput.config(state=tk.NORMAL)
        # 在文本框末尾插入文本
        self.textOutput.insert(tk.END, s)
        # 再次禁用文本框
        self.textOutput.config(state=tk.DISABLED)
        # 获取当前文本框的垂直视图
        yview = self.textOutput.yview()
        # 如果视图的底部大于0.5或非常接近1，则滚动到文本框的末尾
        if yview[1] - yview[0] > .5 or yview[1] > .9:
            self.textOutput.see('end')

    # 获取配置参数的函数
    def getConfigParams(self) -> param.REConfigParams:
        # 初始化重采样尺寸值
        resizeModeValue = 0
        # 根据选择的重采样模式设置resizeModeValue
        match self.varintResizeMode.get():
            case param.ResizeMode.RATIO:
                resizeModeValue = self.varintResizeRatio.get()
            case param.ResizeMode.WIDTH:
                resizeModeValue = self.varintResizeWidth.get()
            case param.ResizeMode.HEIGHT:
                resizeModeValue = self.varintResizeHeight.get()
        # 返回配置参数对象
        return param.REConfigParams(
            self.varstrModel.get(),
            self.modelFactors[self.varstrModel.get()],
            self.varintResizeMode.get(),
            resizeModeValue,
            self.downsample[self.varintDownsampleIndex.get()][1],
            self.tileSize[self.varintTileSizeIndex.get()],
            self.varintGPUID.get(),
            self.varboolUseTTA.get(),
        )
# 定义一个函数，用于获取输出文件的路径。函数接收一个路径参数p，并返回一个字符串。
    def getOutputPath(self, p: str) -> str:
        # 检查传入的路径p是否是一个目录，如果是，设置base为p，扩展名为空字符串''。
        if os.path.isdir(p):
            base, ext = p, ''
        else:
            # 如果p不是目录，使用os.path.splitext()函数分离出文件的基础名和扩展名。
            base, ext = os.path.splitext(p)
            # 如果文件扩展名为.jpg，将其更改为.png。
            if ext.lower() == '.jpg':
                ext = '.png'
            # 如果文件扩展名为.png并且一个布尔变量varboolUseWebP为真，则将扩展名更改为.webp。
            if ext.lower() == '.png' and self.varboolUseWebP.get():
                ext = '.webp'
        # 初始化一个空的后缀字符串。
        suffix = ''
        # 使用match-case语句来根据varintResizeMode的值设置suffix。
        match self.varintResizeMode.get():
            # 如果模式是RATIO，suffix设置为'x'后跟一个变量ResizeRatio的值。
            case param.ResizeMode.RATIO:
                suffix = f'x{self.varintResizeRatio.get()}'
            # 如果模式是WIDTH，suffix设置为'w'后跟一个变量ResizeWidth的值。
            case param.ResizeMode.WIDTH:
                suffix = f'w{self.varintResizeWidth.get()}'
            # 如果模式是HEIGHT，suffix设置为'h'后跟一个变量ResizeHeight的值。
            case param.ResizeMode.HEIGHT:
                suffix = f'h{self.varintResizeHeight.get()}'
        # 返回最终的文件路径，格式为base-suffix.ext。
        return f'{base}-{suffix}{ext}'

# 主程序入口点。
if __name__ == '__main__':
    # 创建一个Tkinter窗口实例，并立即隐藏它。
    root = TkinterDnD.Tk()
    root.withdraw()

    # 检查Real-ESRGAN-ncnn-vulkan主程序是否存在于指定的APP_PATH路径下。
    if not os.path.exists(os.path.join(APP_PATH, 'realesrgan-ncnn-vulkan' + ('.exe' if os.name == 'nt' else ''))):
        # 如果主程序未找到，显示一个警告消息框。
        messagebox.showwarning(
            '未找到主程序',
            '未找到 Real-ESRGAN-ncnn-vulkan 主程序。\n请前往 https://github.com/xinntao/Real-ESRGAN/releases 下载，并将本文件和主程序放在同一目录下。',
        )
        # 打开默认的网络浏览器，跳转到Real-ESRGAN的GitHub发布页面。
        webbrowser.open_new_tab('https://github.com/xinntao/Real-ESRGAN/releases')
        # 退出程序。
        sys.exit(0)

    # 设置窗口标题为'Real-ESRGAN GUI'。
    root.title('Real-ESRGAN GUI')
    try:
        # 尝试设置窗口图标。
        root.iconbitmap(os.path.join(BASE_PATH, 'icon-256px.ico'))
    except tk.TclError:
        # 如果设置图标失败，使用PhotoImage设置窗口图标。
        root.tk.call('wm', 'iconphoto', root._w, ImageTk.PhotoImage(Image.open(os.path.join(BASE_PATH, 'icon-256px.ico'))))

    # 加载主题配置文件，并根据系统是否处于暗模式设置主题。
    root.tk.call('source', os.path.join(BASE_PATH, 'theme/sun-valley.tcl'))
    root.tk.call('set_theme', 'dark' if darkdetect.isDark() else 'light')

    # 创建REGUIApp类的实例。
    app = REGUIApp(root)
    # 为应用注册拖放目标。
    app.drop_target_register(DND_FILES)
    # 绑定拖放事件，当文件被拖放到应用上时，调用setInputPath方法。
    app.dnd_bind(
        '<<Drop>>',
        lambda e: app.setInputPath(e.data[1:-1] if '{' == e.data[0] and '}' == e.data[-1] else e.data),
    )
    # 将app组件填充到root窗口中。
    app.pack(fill=tk.BOTH, expand=True)

    # 设置窗口的初始大小。
    initialSize = (720, 540)
    # 设置窗口的最小尺寸。
    root.minsize(*initialSize)
    # 设置窗口的初始位置，居中显示。
    root.geometry('{}x{}+{}+{}'.format(
        *initialSize,
        (root.winfo_screenwidth() - initialSize[0]) // 2,
        (root.winfo_screenheight() - initialSize[1]) // 2,
    ))

    # 显示窗口。
    root.deiconify()
    # 进入Tkinter事件循环。
    root.mainloop()