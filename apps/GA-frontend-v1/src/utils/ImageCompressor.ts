// src/utils/ImageCompressor.ts

/**
 * 图片压缩配置接口
 */
export interface ImageCompressionOptions {
  /** 最大尺寸（宽度或高度），默认1024px */
  maxSize?: number;
  /** 压缩质量（0-1之间的值），默认0.7 */
  quality?: number;
  /** 小文件阈值（小于此值的文件不压缩），默认100KB */
  smallFileThreshold?: number;
}

/**
 * 图片压缩工具类
 */
export class ImageCompressor {
  /** 默认配置 */
  private static readonly DEFAULT_OPTIONS: ImageCompressionOptions = {
    maxSize: 1024,
    quality: 0.7,
    smallFileThreshold: 100 * 1024, // 100KB
  };

  /**
   * 压缩图片文件
   * @param file 图片文件
   * @param options 压缩配置选项
   * @returns Promise<string> 压缩后的图片DataURL
   */
  public static async compress(file: File, options: ImageCompressionOptions = {}): Promise<string> {
    // 合并默认配置和用户配置
    const mergedOptions = { ...this.DEFAULT_OPTIONS, ...options };
    
    // 检查文件类型是否为图片
    if (!file.type.startsWith('image/')) {
      throw new Error('请选择有效的图片文件');
    }
    
    // 对于小文件，直接返回原始数据
    if (file.size < mergedOptions.smallFileThreshold!) {
      return this.fileToDataURL(file);
    }
    
    // 大文件进行压缩处理
    return this.doCompress(file, mergedOptions);
  }

  /**
   * 将文件转换为DataURL
   * @param file 文件对象
   * @returns Promise<string> 文件的DataURL表示
   */
  private static fileToDataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        if (e.target && typeof e.target.result === 'string') {
          resolve(e.target.result);
        } else {
          reject(new Error('文件读取失败'));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('文件读取错误'));
      };
      
      reader.readAsDataURL(file);
    });
  }

  /**
   * 执行图片压缩
   * @param file 图片文件
   * @param options 压缩配置
   * @returns Promise<string> 压缩后的图片DataURL
   */
  private static async doCompress(file: File, options: ImageCompressionOptions): Promise<string> {
    const dataUrl = await this.fileToDataURL(file);
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      
      img.onload = () => {
        // 创建canvas元素
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        if (!ctx) {
          reject(new Error('无法创建Canvas上下文'));
          return;
        }
        
        // 计算压缩后的尺寸，保持原比例
        let width = img.width;
        let height = img.height;
        const maxSize = options.maxSize!;
        
        if (width > height) {
          if (width > maxSize) {
            height *= maxSize / width;
            width = maxSize;
          }
        } else {
          if (height > maxSize) {
            width *= maxSize / height;
            height = maxSize;
          }
        }
        
        // 设置canvas尺寸
        canvas.width = Math.floor(width);
        canvas.height = Math.floor(height);
        
        // 在canvas上绘制图片
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // 获取压缩后的DataURL
        const compressedDataUrl = canvas.toDataURL(file.type, options.quality);
        resolve(compressedDataUrl);
      };
      
      img.onerror = () => {
        reject(new Error('图片加载失败'));
      };
      
      img.src = dataUrl;
    });
  }

  /**
   * 检查文件是否为图片
   * @param file 待检查的文件
   * @returns boolean 是否为图片文件
   */
  public static isImageFile(file: File): boolean {
    return file.type.startsWith('image/');
  }

  /**
   * 获取图片尺寸信息
   * @param dataUrl 图片的DataURL
   * @returns Promise<{width: number, height: number}> 图片尺寸信息
   */
  public static getImageDimensions(dataUrl: string): Promise<{width: number, height: number}> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      
      img.onload = () => {
        resolve({ width: img.width, height: img.height });
      };
      
      img.onerror = () => {
        reject(new Error('图片加载失败'));
      };
      
      img.src = dataUrl;
    });
  }
}

// 导出默认实例
export default new ImageCompressor();