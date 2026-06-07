import { useEffect, useState } from 'react';
import { FolderKanban, Plus, Edit, Trash2, RefreshCw, Check, X } from 'lucide-react';
import { useProjectStore, type Project } from '../../stores/projectStore';

export function ProjectPage() {
  const { projects, fetchProjects, createProject, updateProject, deleteProject } = useProjectStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = () => {
    setEditingProject(null);
    setFormData({ name: '', description: '' });
    setIsModalOpen(true);
  };

  const handleEditProject = (project: Project) => {
    setEditingProject(project);
    setFormData({
      name: project.name,
      description: project.description,
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingProject) {
      await updateProject(editingProject.project_id, formData);
    } else {
      await createProject(formData);
    }
    setIsModalOpen(false);
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-[#165DFF]" />
            项目管理
          </h1>
          <p className="text-[#64748b] text-sm mt-1">管理您的测试项目</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchProjects}
            className="px-4 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] rounded-lg flex items-center gap-2 transition-all duration-200"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
          <button
            onClick={handleCreateProject}
            className="px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white rounded-lg flex items-center gap-2 transition-all duration-200"
          >
            <Plus className="w-4 h-4" />
            新建项目
          </button>
        </div>
      </div>

      {/* Project Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <div
            key={project.project_id}
            className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#e8f0fe] rounded-lg flex items-center justify-center shrink-0">
                  <FolderKanban className="w-5 h-5 text-[#165DFF]" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-[#0f172a] font-medium text-sm truncate">{project.name}</h3>
                  {project.task_count !== undefined && (
                    <span className="px-2 py-0.5 bg-[#f1f5f9] text-[#64748b] text-xs rounded">
                      {project.task_count} 任务
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => handleEditProject(project)}
                  className="p-1.5 text-[#94a3b8] hover:text-[#165DFF] hover:bg-[#e8f0fe] rounded-lg transition-all duration-200"
                  title="编辑"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => { if (confirm('确定要删除此项目吗？')) { deleteProject(project.project_id); } }}
                  className="p-1.5 text-[#94a3b8] hover:text-[#ef4444] hover:bg-[#fef2f2] rounded-lg transition-all duration-200"
                  title="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <p className="text-[#64748b] text-xs mb-3 line-clamp-2">{project.description || '暂无描述'}</p>

            <div className="flex items-center justify-between">
              <span className="text-xs text-[#94a3b8]">{new Date(project.created_at).toLocaleDateString()}</span>
              {project.updated_at && (
                <span className="text-xs text-[#cbd5e1]">更新: {new Date(project.updated_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {projects.length === 0 && (
        <div className="text-center py-16 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg">
          <FolderKanban className="w-12 h-12 text-[#94a3b8] mx-auto mb-3" />
          <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无项目</h3>
          <p className="text-[#64748b] text-sm">创建您的第一个测试项目</p>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 w-full max-w-md mx-4 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-[#0f172a]">
                {editingProject ? '编辑项目' : '新建项目'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-all duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[#64748b] text-sm mb-2">项目名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  placeholder="输入项目名称"
                  required
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-sm mb-2">项目描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] resize-none transition-all duration-200"
                  rows={3}
                  placeholder="输入项目描述"
                  required
                />
              </div>

              <div className="flex gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] rounded-lg text-sm font-medium transition-all duration-200"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200"
                >
                  <Check className="w-4 h-4" />
                  {editingProject ? '保存' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
