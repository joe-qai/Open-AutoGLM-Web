import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from './Sidebar';
import { MemoryRouter } from 'react-router-dom';

describe('Sidebar Component', () => {
  it('renders LOCKIN logo when expanded', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    
    const logoText = screen.getByText('LOCKIN');
    expect(logoText).toBeInTheDocument();
    expect(logoText).toHaveClass('font-semibold', 'text-white');
  });

  it('collapses and expands on toggle', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    
    const logoText = screen.getByText('LOCKIN');
    expect(logoText).toBeInTheDocument();
    
    const toggleButton = screen.getByRole('button');
    fireEvent.click(toggleButton);
    
    expect(logoText).not.toBeInTheDocument();
    
    fireEvent.click(toggleButton);
    expect(screen.getByText('LOCKIN')).toBeInTheDocument();
  });

  it('renders all navigation items', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    
    const navLabels = ['仪表盘', '项目管理', 'APK管理', 'Agent脚本', '脚本管理', '设备管理', '任务管理', '设置'];
    
    navLabels.forEach(label => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('shows version info when expanded', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    
    const versionText = screen.getByText('v1.0.0');
    expect(versionText).toBeInTheDocument();
  });

  it('navigates to dashboard by default', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    
    const dashboardLink = screen.getByText('仪表盘');
    expect(dashboardLink.parentElement).toHaveClass('bg-indigo-600', 'text-white');
  });
});
