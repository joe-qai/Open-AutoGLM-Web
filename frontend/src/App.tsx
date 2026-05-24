import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { AgentPage } from './pages/Agent/AgentPage';
import { DevicePage } from './pages/Device/DevicePage';
import { TaskPage } from './pages/Task/TaskPage';
import { ScriptPage } from './pages/Script/ScriptPage';
import { ProjectPage } from './pages/Project/ProjectPage';
import { ApkPage } from './pages/Apk/ApkPage';
import { SettingsPage } from './pages/Settings/SettingsPage';
import { ReportPage } from './pages/Report/ReportPage';
import { LogsPage } from './pages/Logs/LogsPage';
import './styles/globals.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="agent" element={<AgentPage />} />
          <Route path="devices" element={<DevicePage />} />
          <Route path="tasks" element={<TaskPage />} />
          <Route path="scripts" element={<ScriptPage />} />
          <Route path="projects" element={<ProjectPage />} />
          <Route path="apk" element={<ApkPage />} />
          <Route path="reports" element={<ReportPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
