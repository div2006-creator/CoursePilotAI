import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Compass,
  LayoutDashboard,
  BookOpen,
  BotMessageSquare,
  CalendarCheck,
  BarChart3,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/courses', label: 'Courses', icon: BookOpen },
    { to: '/tutor', label: 'AI Tutor', icon: BotMessageSquare },
    { to: '/study-plan', label: 'Study Plan', icon: CalendarCheck },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-xl text-gray-900 tracking-tight">CoursePilot</span>
              <span className="text-xs font-semibold text-indigo-600 ml-1.5 uppercase px-2 py-0.5 bg-indigo-50 rounded-full border border-indigo-100">
                AI
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-4">
            <nav className="flex space-x-1 sm:space-x-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      `flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-700'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden md:inline">{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            {user && (
              <div className="flex items-center space-x-3 pl-2 sm:pl-4 border-l border-gray-200">
                <span
                  className="hidden lg:inline text-sm font-medium text-gray-700 truncate max-w-[160px]"
                  title={user.email}
                >
                  {user.name}
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-red-700 hover:bg-red-50 transition-colors"
                  title="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
