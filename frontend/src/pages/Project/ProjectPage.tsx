import { useEffect, useState } from 'react';
import { FolderKanban, Plus, MoreVertical, Edit, Trash2, RefreshCw, Check, X } from 'lucide-react';
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FolderKanban className="w-6 h-6 text-indigo-400" />
            项目管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试项目</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchProjects}
            className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
          <button
            onClick={handleCreateProject}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors"
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
            className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 hover:border-[#475569] transition-colors"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-[#0f172a] rounded-xl flex items-center justify-center">
                  <FolderKanban className="w-6 h-6 text-[#64748b]" />
                </div>
                <div>
                  <h3 className="text-white font-medium">{project.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    {project.task_count !== undefined && (
                      <span className="text-[#64748b] text-sm">{project.task_count} 个任务</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="relative group">
                <button className="p-1 hover:bg-[#334155] rounded-lg transition-colors">
                  <MoreVertical className="w-4 h-4 text-[#64748b]" />
                </button>
                <div className="absolute right-0 top-0 mt-8 w-32 bg-[#1e293b] border border-[#334155] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                  <button
                    onClick={() => handleEditProject(project)}
                    className="w-full px-4 py-2 text-left text-sm text-[#94a3b8] hover:text-white hover:bg-[#334155] flex items-center gap-2 rounded-t-lg"
                  >
                    <Edit className="w-4 h-4" />
                    编辑
                  </button>
                  <button
                    onClick={() => deleteProject(project.project_id)}
                    className="w-full px-4 py-2 text-left text-sm text-red-400 hover:text-red-300 hover:bg-[#334155] flex items-center gap-2 rounded-b-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                    删除
                  </button>
                </div>
              </div>
            </div>

            <p className="text-[#94a3b8] text-sm mb-4 line-clamp-2">{project.description}</p>

            <div className="flex items-center justify-between text-xs text-[#64748b]">
              <span>创建于 {new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>

      {projects.length === 0 && (
        <div className="text-center py-20">
          <FolderKanban className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无项目</h3>
          <p className="text-[#64748b] mb-4">创建您的第一个测试项目</p>
          <button
            onClick={handleCreateProject}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 mx-auto transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建项目
          </button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">
                {editingProject ? '编辑项目' : '新建项目'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">项目名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="输入项目名称"
                  required
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">项目描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500 resize-none"
                  rows={3}
                  placeholder="输入项目描述"
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
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
