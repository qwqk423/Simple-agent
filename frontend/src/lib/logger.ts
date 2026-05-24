/**
 * 前端日志工具类
 * 支持颜色区分、级别控制、仅在错误时显示详细日志
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogConfig {
  level: LogLevel;
  showTimestamp: boolean;
  showLevel: boolean;
  showModule: boolean;
  // 是否在正常时隐藏 debug/info 日志（仅在错误时显示）
  silentInProduction: boolean;
}

// 日志级别优先级
const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// 日志颜色配置
const LEVEL_COLORS: Record<LogLevel, string> = {
  debug: '#6b7280', // gray-500
  info: '#3b82f6',  // blue-500
  warn: '#f59e0b',  // amber-500
  error: '#ef4444', // red-500
};

const LEVEL_BG_COLORS: Record<LogLevel, string> = {
  debug: 'background: #374151; color: #9ca3af; padding: 2px 6px; border-radius: 3px;',
  info: 'background: #1e40af; color: #60a5fa; padding: 2px 6px; border-radius: 3px;',
  warn: 'background: #92400e; color: #fbbf24; padding: 2px 6px; border-radius: 3px;',
  error: 'background: #991b1b; color: #fca5a5; padding: 2px 6px; border-radius: 3px; font-weight: bold;',
};

// 模块颜色（用于区分不同模块的日志）
const MODULE_COLORS = [
  '#22d3ee', // cyan
  '#a78bfa', // purple
  '#f472b6', // pink
  '#34d399', // emerald
  '#fbbf24', // amber
  '#60a5fa', // blue
  '#f87171', // red
  '#a3e635', // lime
];

class Logger {
  private config: LogConfig;
  private moduleName: string;
  private moduleColor: string;
  private errorHistory: Map<string, number> = new Map();
  private readonly ERROR_COOLDOWN = 5000; // 相同错误5秒内不重复打印

  constructor(moduleName: string, config: Partial<LogConfig> = {}) {
    this.moduleName = moduleName;
    this.moduleColor = this.getModuleColor(moduleName);
    this.config = {
      level: (process.env.NODE_ENV === 'development' ? 'debug' : 'info') as LogLevel,
      showTimestamp: true,
      showLevel: true,
      showModule: true,
      silentInProduction: true,
      ...config,
    };
  }

  private getModuleColor(moduleName: string): string {
    let hash = 0;
    for (let i = 0; i < moduleName.length; i++) {
      hash = moduleName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % MODULE_COLORS.length;
    return MODULE_COLORS[index];
  }

  private shouldLog(level: LogLevel): boolean {
    return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[this.config.level];
  }

  private isSilentMode(): boolean {
    return this.config.silentInProduction && process.env.NODE_ENV === 'production';
  }

  private formatTimestamp(): string {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  private createLogStyles(level: LogLevel): string[] {
    const styles: string[] = [];
    
    if (this.config.showTimestamp) {
      styles.push('color: #6b7280; font-size: 11px;');
    }
    
    if (this.config.showLevel) {
      styles.push(LEVEL_BG_COLORS[level]);
    }
    
    if (this.config.showModule) {
      styles.push(`color: ${this.moduleColor}; font-weight: 600;`);
    }
    
    return styles;
  }

  private formatMessage(level: LogLevel, message: string): [string, string[]] {
    const parts: string[] = [];
    const styles: string[] = [];
    
    if (this.config.showTimestamp) {
      parts.push(`%c${this.formatTimestamp()}`);
      styles.push('color: #6b7280; font-size: 11px;');
    }
    
    if (this.config.showLevel) {
      parts.push(`%c${level.toUpperCase()}`);
      styles.push(LEVEL_BG_COLORS[level]);
    }
    
    if (this.config.showModule) {
      parts.push(`%c[${this.moduleName}]`);
      styles.push(`color: ${this.moduleColor}; font-weight: 600;`);
    }
    
    parts.push(`%c${message}`);
    styles.push(`color: ${level === 'error' ? '#fca5a5' : level === 'warn' ? '#fbbf24' : 'inherit'};`);
    
    return [parts.join(' '), styles];
  }

  private shouldSuppressError(errorKey: string): boolean {
    const now = Date.now();
    const lastTime = this.errorHistory.get(errorKey);
    if (lastTime && now - lastTime < this.ERROR_COOLDOWN) {
      return true;
    }
    this.errorHistory.set(errorKey, now);
    // 清理过期的错误记录
    this.errorHistory.forEach((time, key) => {
      if (now - time > this.ERROR_COOLDOWN * 2) {
        this.errorHistory.delete(key);
      }
    });
    return false;
  }

  // 基础日志方法
  debug(message: string, ...args: any[]): void {
    if (!this.shouldLog('debug')) return;
    if (this.isSilentMode()) return;
    
    const [formattedMessage, styles] = this.formatMessage('debug', message);
    console.debug(formattedMessage, ...styles, ...args);
  }

  info(message: string, ...args: any[]): void {
    if (!this.shouldLog('info')) return;
    if (this.isSilentMode()) return;
    
    const [formattedMessage, styles] = this.formatMessage('info', message);
    console.info(formattedMessage, ...styles, ...args);
  }

  warn(message: string, ...args: any[]): void {
    if (!this.shouldLog('warn')) return;
    
    const [formattedMessage, styles] = this.formatMessage('warn', message);
    console.warn(formattedMessage, ...styles, ...args);
  }

  error(message: string, error?: any, ...args: any[]): void {
    if (!this.shouldLog('error')) return;
    
    // 防止相同错误刷屏
    const errorKey = `${this.moduleName}:${message}`;
    if (this.shouldSuppressError(errorKey)) {
      return;
    }
    
    const [formattedMessage, styles] = this.formatMessage('error', message);
    
    // 打印主错误信息
    console.error(formattedMessage, ...styles);
    
    // 打印错误详情
    if (error) {
      if (error instanceof Error) {
        const errorDetails: any = {
          name: error.name,
          message: error.message,
        };
        // 只在开发环境显示堆栈
        if (process.env.NODE_ENV === 'development' && error.stack) {
          errorDetails.stack = error.stack.split('\n').slice(0, 5).join('\n');
        }
        if (args.length > 0) {
          errorDetails.context = args.length === 1 ? args[0] : args;
        }
        console.error('%c错误详情:', 'color: #ef4444; font-weight: bold;', errorDetails);
      } else if (typeof error === 'object' && Object.keys(error).length === 0) {
        // 空对象，显示上下文
        console.error('%c错误详情:', 'color: #ef4444; font-weight: bold;', '(空对象)', ...args);
      } else {
        console.error('%c错误详情:', 'color: #ef4444; font-weight: bold;', error, ...args);
      }
    }
  }

  // 分组日志（用于复杂操作的跟踪）
  group(label: string, collapsed: boolean = false): void {
    if (this.isSilentMode() && this.config.level === 'debug') return;
    
    const style = `color: ${this.moduleColor}; font-weight: bold;`;
    if (collapsed) {
      console.groupCollapsed(`%c[${this.moduleName}] ${label}`, style);
    } else {
      console.group(`%c[${this.moduleName}] ${label}`, style);
    }
  }

  groupEnd(): void {
    console.groupEnd();
  }

  // 性能计时
  time(label: string): void {
    if (this.isSilentMode()) return;
    console.time(`[${this.moduleName}] ${label}`);
  }

  timeEnd(label: string): void {
    if (this.isSilentMode()) return;
    console.timeEnd(`[${this.moduleName}] ${label}`);
  }

  // API 调用专用日志
  logApiCall(method: string, url: string, data?: any): void {
    if (!this.shouldLog('info')) return;
    if (this.isSilentMode()) return;
    
    const [formattedMessage, styles] = this.formatMessage('info', `🌐 ${method} ${url}`);
    console.info(formattedMessage, ...styles);
    if (data && Object.keys(data).length > 0) {
      console.info('%c请求数据:', `color: ${LEVEL_COLORS.info};`, data);
    }
  }

  logApiResponse(method: string, url: string, status: number, data?: any): void {
    const isError = status >= 400;
    const level: LogLevel = isError ? 'error' : 'info';
    
    if (!this.shouldLog(level)) return;
    
    const emoji = isError ? '❌' : '✅';
    const [formattedMessage, styles] = this.formatMessage(level, `${emoji} ${method} ${url} (${status})`);
    
    if (isError) {
      console.error(formattedMessage, ...styles);
      if (data) {
        console.error('%c响应数据:', 'color: #ef4444;', data);
      }
    } else {
      if (!this.isSilentMode()) {
        console.info(formattedMessage, ...styles);
      }
    }
  }

  // 状态变更日志
  logStateChange(stateName: string, oldValue: any, newValue: any): void {
    if (!this.shouldLog('debug')) return;
    if (this.isSilentMode()) return;
    
    const [formattedMessage, styles] = this.formatMessage('debug', `📝 ${stateName} 变更`);
    console.debug(formattedMessage, ...styles, { oldValue, newValue });
  }

  // 用户操作日志
  logUserAction(action: string, details?: any): void {
    if (!this.shouldLog('info')) return;
    
    const [formattedMessage, styles] = this.formatMessage('info', `👤 用户操作: ${action}`);
    console.info(formattedMessage, ...styles);
    if (details) {
      console.info('%c操作详情:', `color: ${LEVEL_COLORS.info};`, details);
    }
  }

  // 设置日志级别
  setLevel(level: LogLevel): void {
    this.config.level = level;
    this.info(`日志级别已设置为: ${level}`);
  }

  // 获取当前配置
  getConfig(): LogConfig {
    return { ...this.config };
  }
}

// 日志管理器
class LoggerManager {
  private loggers = new Map<string, Logger>();
  private globalConfig: Partial<LogConfig> = {};

  getLogger(moduleName: string): Logger {
    if (!this.loggers.has(moduleName)) {
      this.loggers.set(moduleName, new Logger(moduleName, this.globalConfig));
    }
    return this.loggers.get(moduleName)!;
  }

  setGlobalConfig(config: Partial<LogConfig>): void {
    this.globalConfig = config;
    this.loggers.forEach(logger => {
      Object.assign(logger, { config: { ...logger.getConfig(), ...config } });
    });
  }

  // 启用/禁用静默模式
  setSilentMode(silent: boolean): void {
    this.setGlobalConfig({ silentInProduction: silent });
  }

  // 设置全局日志级别
  setGlobalLevel(level: LogLevel): void {
    this.setGlobalConfig({ level });
  }
}

const loggerManager = new LoggerManager();

// 导出获取 logger 的函数
export function getLogger(moduleName: string): Logger {
  return loggerManager.getLogger(moduleName);
}

// 导出日志管理器的方法
export function setGlobalLogLevel(level: LogLevel): void {
  loggerManager.setGlobalLevel(level);
}

export function setSilentMode(silent: boolean): void {
  loggerManager.setSilentMode(silent);
}

// 导出 Logger 类以便需要时自定义
export { Logger, loggerManager };
