import { Package, Upload, Trash2, FolderOpen, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { useRef, useEffect } from 'react';
import { useApkStore } from '../../stores/apkStore';

export function ApkPage() {
  const { apks, loading, uploading, error, success, fetchApks, uploadApk, deleteApk, clearMessages } = useApkStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchApks();
  }, [fetchApks]);

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => clearMessages(), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success, clearMessages]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.apk')) {
      uploadApk(file);
    } else if (file) {
      alert('请选择APK文件');
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '未知';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Package className="w-6 h-6 text-indigo-400" />
            APK管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试APK文件</p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? '上传中...' : '上传APK'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".apk"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-300">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-900/30 border border-green-500/30 rounded-lg flex items-center gap-2 text-green-300">
          <CheckCircle className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* APK List */}
      {loading ? (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-8 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mr-2" />
          <span className="text-[#94a3b8]">加载中...</span>
        </div>
      ) : apks.length === 0 ? (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无APK文件</h3>
            <p className="text-[#64748b]">上传您的第一个APK文件开始测试</p>
          </div>
        </div>
      ) : (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#0f172a] border-b border-[#334155]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    APK信息
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    原始文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    版本号
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    包名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    大小
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    上传时间
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#334155]">
                {apks.map((apk) => (
                  <tr key={apk.id} className="hover:bg-[#0f172a]/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center">
                            <Package className="w-5 h-5 text-indigo-400" />
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-white">{apk.name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {apk.original_filename || apk.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {apk.version || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8] font-mono">
                      {apk.package_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {formatFileSize(apk.file_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {formatDate(apk.upload_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => deleteApk(apk.id)}
                        className="text-red-400 hover:text-red-300 flex items-center gap-1"
                      >
                        <Trash2 className="w-4 h-4" />
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}