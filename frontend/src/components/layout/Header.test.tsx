import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from './Header';

describe('Header Component', () => {
  it('renders platform title correctly', () => {
    render(<Header />);
    const titleElement = screen.getByText('LOCKIN Agent Platform');
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveClass('text-lg', 'font-semibold', 'text-white');
  });

  it('renders search input with placeholder', () => {
    render(<Header />);
    const searchInput = screen.getByPlaceholderText('搜索...');
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute('type', 'text');
  });

  it('updates search input value on change', () => {
    render(<Header />);
    const searchInput = screen.getByPlaceholderText('搜索...');
    
    fireEvent.change(searchInput, { target: { value: 'test search' } });
    expect(searchInput).toHaveValue('test search');
  });

  it('renders notification button with badge', () => {
    render(<Header />);
    const buttons = screen.getAllByRole('button');
    const notificationButton = buttons.find(btn => btn.querySelector('svg.lucide-bell'));
    expect(notificationButton).toBeInTheDocument();
    
    const badge = notificationButton?.querySelector('span');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-red-500');
  });

  it('renders user info correctly', () => {
    render(<Header />);
    const adminText = screen.getByText('管理员');
    const emailText = screen.getByText('admin@lockin.com');
    
    expect(adminText).toBeInTheDocument();
    expect(emailText).toBeInTheDocument();
  });
});
