"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Sparkles, Image, X, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getLogger } from "@/lib/logger";

const logger = getLogger('ChatInput');

interface ChatInputProps {
  onSend: (message: string, images?: string[]) => void;
  onCommand?: (command: string) => void;
  disabled?: boolean;
  expanded?: boolean;
}

// 图片大小限制：10MB
const MAX_IMAGE_SIZE = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
// 最多上传图片数量
const MAX_IMAGES = 5;
// 压缩后最短边像素
const TARGET_MIN_SIZE = 1000;

/**
 * 图片压缩函数
 * 使用 Canvas 进行高质量缩放（模拟 Lanczos3 效果）
 * 将图片最短边缩小到 1000 像素，长边等比例缩小
 * 如果短边已经小于 1000 像素，则跳过压缩，直接转为 PNG base64
 */
const compressImage = async (file: File): Promise<string> => {
  // 确保在浏览器环境中运行
  if (typeof window === 'undefined') {
    throw new Error('图片压缩只能在浏览器环境中运行');
  }

  logger.time(`图片压缩: ${file.name}`);

  return new Promise((resolve, reject) => {
    const img = document.createElement('img');
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      const { width, height } = img;
      const minSide = Math.min(width, height);

      // 如果最短边已经小于 1000 像素，直接转为 PNG base64，不进行缩放
      if (minSide <= TARGET_MIN_SIZE) {
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        if (!ctx) {
          logger.error('创建 canvas context 失败');
          reject(new Error('无法创建 canvas context'));
          return;
        }

        // 使用高质量图像平滑
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, width, height);

        // 转为 PNG base64
        const base64 = canvas.toDataURL('image/png');
        logger.timeEnd(`图片压缩: ${file.name}`);
        logger.debug(`图片无需压缩: ${file.name} (${width}x${height})`);
        resolve(base64);
        return;
      }

      // 需要压缩：计算新的尺寸
      let newWidth: number;
      let newHeight: number;

      if (width < height) {
        // 宽是短边
        newWidth = TARGET_MIN_SIZE;
        newHeight = Math.round((height / width) * TARGET_MIN_SIZE);
      } else {
        // 高是短边（或相等）
        newHeight = TARGET_MIN_SIZE;
        newWidth = Math.round((width / height) * TARGET_MIN_SIZE);
      }

      logger.debug(`图片压缩: ${file.name} ${width}x${height} -> ${newWidth}x${newHeight}`);

      // 创建 canvas 进行缩放
      const canvas = document.createElement('canvas');
      canvas.width = newWidth;
      canvas.height = newHeight;
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        logger.error('创建 canvas context 失败');
        reject(new Error('无法创建 canvas context'));
        return;
      }

      // 使用高质量图像平滑（模拟 Lanczos3 效果）
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      // 使用多步缩放以获得更好的质量（模拟 Lanczos3）
      // 如果缩小比例很大，分步进行
      let currentWidth = width;
      let currentHeight = height;
      const stepCanvas = document.createElement('canvas');
      const stepCtx = stepCanvas.getContext('2d');

      if (!stepCtx) {
        logger.error('创建 step canvas context 失败');
        reject(new Error('无法创建 step canvas context'));
        return;
      }

      // 多步缩放：每次最多缩小到原来的 0.5 倍，直到达到目标尺寸
      let sourceCanvas: HTMLCanvasElement | HTMLImageElement = img;

      while (currentWidth > newWidth * 2 || currentHeight > newHeight * 2) {
        currentWidth = Math.max(currentWidth * 0.5, newWidth);
        currentHeight = Math.max(currentHeight * 0.5, newHeight);

        stepCanvas.width = currentWidth;
        stepCanvas.height = currentHeight;
        stepCtx.imageSmoothingEnabled = true;
        stepCtx.imageSmoothingQuality = 'high';
        stepCtx.drawImage(
          sourceCanvas,
          0, 0,
          sourceCanvas instanceof HTMLImageElement ? sourceCanvas.naturalWidth : sourceCanvas.width,
          sourceCanvas instanceof HTMLImageElement ? sourceCanvas.naturalHeight : sourceCanvas.height,
          0, 0,
          currentWidth,
          currentHeight
        );

        sourceCanvas = stepCanvas;
      }

      // 最后一步：缩放到目标尺寸
      ctx.drawImage(
        sourceCanvas,
        0, 0,
        sourceCanvas instanceof HTMLImageElement ? sourceCanvas.naturalWidth : sourceCanvas.width,
        sourceCanvas instanceof HTMLImageElement ? sourceCanvas.naturalHeight : sourceCanvas.height,
        0, 0,
        newWidth,
        newHeight
      );

      // 转为 PNG base64
      const base64 = canvas.toDataURL('image/png');
      logger.timeEnd(`图片压缩: ${file.name}`);
      resolve(base64);
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      logger.error(`图片加载失败: ${file.name}`);
      reject(new Error('图片加载失败'));
    };

    img.src = url;
  });
};

export function ChatInput({ onSend, onCommand, disabled, expanded = false }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isCompressing, setIsCompressing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  logger.debug('ChatInput 渲染', { 
    inputLength: input.length, 
    selectedImages: selectedImages.length,
    isCompressing,
    isDragging 
  });

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = expanded ? 200 : 100;
      const minHeight = expanded ? 100 : 25;
      const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight);
      textarea.style.height = `${newHeight}px`;
    }
  }, [input, expanded]);

  // 验证并处理文件
  const processFiles = async (files: FileList | null): Promise<void> => {
    if (!files || files.length === 0) {
      logger.debug('没有选择文件');
      return;
    }

    logger.info(`开始处理 ${files.length} 个文件`);
    setIsCompressing(true);
    const newImages: string[] = [];
    const errors: string[] = [];

    for (let i = 0; i < files.length; i++) {
      // 检查数量限制
      if (selectedImages.length + newImages.length >= MAX_IMAGES) {
        errors.push(`最多只能上传 ${MAX_IMAGES} 张图片`);
        logger.warn(`超过最大图片数量限制: ${MAX_IMAGES}`);
        break;
      }

      const file = files[i];
      logger.debug(`处理文件: ${file.name} (${file.type}, ${(file.size / 1024 / 1024).toFixed(2)}MB)`);

      // 检查文件类型
      if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        errors.push(`${file.name}: 不支持的格式`);
        logger.warn(`不支持的图片格式: ${file.type}`);
        continue;
      }

      // 检查文件大小
      if (file.size > MAX_IMAGE_SIZE) {
        errors.push(`${file.name}: 超过10MB限制`);
        logger.warn(`图片超过大小限制: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
        continue;
      }

      // 压缩图片并转为 base64
      try {
        const base64 = await compressImage(file);
        newImages.push(base64);
        logger.info(`图片处理成功: ${file.name}`);
      } catch (error) {
        logger.error(`图片压缩失败: ${file.name}`, error);
        errors.push(`${file.name}: 压缩失败`);
      }
    }

    setIsCompressing(false);

    if (newImages.length > 0) {
      setSelectedImages(prev => [...prev, ...newImages]);
      logger.info(`成功添加 ${newImages.length} 张图片`);
    }

    if (errors.length > 0) {
      logger.warn('图片处理出现错误', errors);
      alert(errors.join('\n'));
    }
  };

  // 文件选择处理
  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    logger.logUserAction('选择图片文件');
    await processFiles(e.target.files);
    // 清空 input 以便可以再次选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 删除单张图片
  const removeImage = (index: number) => {
    logger.logUserAction('删除图片', { index });
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
  };

  // 拖拽事件处理
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
      logger.debug('拖拽进入输入区域');
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // 确保是离开整个区域，而不是子元素
    if (e.currentTarget === e.target) {
      setIsDragging(false);
      logger.debug('拖拽离开输入区域');
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) {
      logger.warn('禁用状态下无法接收拖拽文件');
      return;
    }

    const files = e.dataTransfer.files;
    logger.logUserAction('拖拽上传文件', { fileCount: files.length });
    await processFiles(files);
  }, [disabled, selectedImages.length]);

  // 粘贴事件处理
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    if (disabled) {
      logger.warn('禁用状态下无法粘贴');
      return;
    }

    const items = e.clipboardData.items;
    const imageItems: DataTransferItem[] = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        imageItems.push(item);
      }
    }

    if (imageItems.length > 0) {
      e.preventDefault(); // 阻止默认粘贴行为
      logger.logUserAction('粘贴图片', { count: imageItems.length });

      const files: File[] = [];
      for (const item of imageItems) {
        const file = item.getAsFile();
        if (file) {
          files.push(file);
        }
      }

      // 创建 FileList 对象
      const dataTransfer = new DataTransfer();
      files.forEach(file => dataTransfer.items.add(file));
      await processFiles(dataTransfer.files);
    }
  }, [disabled, selectedImages.length]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if ((trimmed || selectedImages.length > 0) && !disabled) {
      if (trimmed.startsWith('/')) {
        const command = trimmed.slice(1);
        logger.logUserAction('执行命令', { command });
        if (onCommand) {
          onCommand(command);
        }
      } else {
        logger.logUserAction('发送消息', { 
          contentLength: trimmed.length, 
          imageCount: selectedImages.length 
        });
        onSend(trimmed, selectedImages.length > 0 ? selectedImages : undefined);
      }
      setInput("");
      setSelectedImages([]);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative p-4 animate-fade-in-up">
      <div className="max-w-4xl mx-auto">
        {/* 图片预览区域 */}
        {selectedImages.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {selectedImages.map((img, index) => (
              <div key={index} className="relative group">
                <div className="w-20 h-20 rounded-xl overflow-hidden border border-border/50 shadow-sm">
                  <img
                    src={img}
                    alt={`预览 ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
                <button
                  onClick={() => removeImage(index)}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                >
                  <X className="w-3 h-3" />
                </button>
                <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[10px] text-center py-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  {index + 1}/{selectedImages.length}
                </div>
              </div>
            ))}
            {/* 添加更多图片按钮 */}
            {selectedImages.length < MAX_IMAGES && (
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isCompressing}
                className="w-20 h-20 rounded-xl border-2 border-dashed border-border/50 flex items-center justify-center text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors disabled:opacity-50"
              >
                <Upload className="w-6 h-6" />
              </button>
            )}
          </div>
        )}

        {/* 压缩中提示 */}
        {isCompressing && (
          <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>图片压缩中...</span>
          </div>
        )}

        {/* 拖拽上传区域 */}
        <div
          ref={dropZoneRef}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className={`
            relative rounded-2xl transition-all duration-300
            ${isDragging ? 'ring-2 ring-primary/50 bg-primary/5' : ''}
          `}
        >
          {/* 拖拽提示遮罩 */}
          {isDragging && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-primary/10 rounded-2xl border-2 border-dashed border-primary/50 backdrop-blur-sm">
              <div className="text-center">
                <Upload className="w-10 h-10 text-primary mx-auto mb-2" />
                <p className="text-sm font-medium text-primary">释放以上传图片</p>
                <p className="text-xs text-muted-foreground mt-1">
                  支持 PNG、JPG、GIF、WebP 格式
                </p>
              </div>
            </div>
          )}

          {/* 浮窗式输入框 */}
          <div
            className={`
              relative rounded-2xl border bg-background/95 backdrop-blur-md p-3 shadow-lg
              transition-all duration-300
              ${isFocused
                ? 'border-primary/30 shadow-xl shadow-primary/10 ring-2 ring-primary/10'
                : 'border-border/50 dark:border-border/30 shadow-lg hover:border-border/70 dark:hover:border-border/50 hover:shadow-xl'
              }
              dark:bg-zinc-800/70
            `}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                setIsFocused(true);
                logger.debug('输入框获得焦点');
              }}
              onBlur={() => {
                setIsFocused(false);
                logger.debug('输入框失去焦点');
              }}
              onPaste={handlePaste}
              placeholder={disabled ? "请稍候..." : "输入消息... 支持粘贴图片、拖拽上传 (输入 /compact 压缩对话)"}
              disabled={disabled}
              className={`
                w-full bg-transparent resize-none outline-none
                px-3 py-2.5 text-sm leading-relaxed
                placeholder:text-muted-foreground/50
                ${expanded ? 'min-h-[100px] max-h-[200px]' : 'min-h-[25px] max-h-[100px]'}
              `}
              rows={1}
            />

            {/* 按钮区域 - 图片按钮左下角，发送按钮右下角 */}
            <div className="flex items-center justify-between mt-2">
              {/* 图片上传按钮 - 左下角 */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleImageSelect}
                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                multiple
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || selectedImages.length >= MAX_IMAGES || isCompressing}
                size="icon"
                variant="ghost"
                className={`
                  h-10 w-10 rounded-xl
                  transition-all duration-300
                  ${selectedImages.length > 0
                    ? 'text-green-500 bg-green-50'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }
                  ${disabled || selectedImages.length >= MAX_IMAGES || isCompressing ? 'opacity-50 cursor-not-allowed' : ''}
                `}
                title={`上传图片 (${selectedImages.length}/${MAX_IMAGES})`}
              >
                <Image className="w-5 h-5" />
              </Button>

              {/* 发送按钮 - 右下角 */}
              <Button
                onClick={handleSubmit}
                disabled={(!input.trim() && selectedImages.length === 0) || disabled || isCompressing}
                size="icon"
                className={`
                  h-10 w-10 rounded-xl
                  transition-all duration-300
                  ${(input.trim() || selectedImages.length > 0) && !disabled && !isCompressing
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/30 hover:-translate-y-0.5'
                    : 'bg-slate-100 text-slate-400 dark:bg-slate-800'
                  }
                `}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* 提示信息 */}
        <div className="mt-2 flex items-center justify-center text-[11px] text-muted-foreground/70">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            内容由AI生成，请仔细甄别
          </span>
        </div>
      </div>
    </div>
  );
}
