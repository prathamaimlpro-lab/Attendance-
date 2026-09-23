import React, { useState } from 'react';
import Login from './components/Login';
import AdminDashboard from './components/AdminDashboard';
import StudentDashboard from './components/StudentDashboard';

export default function App() {
  const [user, setUser] = useState(null); // 'admin' or 'student'

  const handleLogin = (role) => {
    setUser(role);
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <div className="min-h-screen flex flex-col justify-between">
      <main className="flex-grow">
        {!user && <Login onLogin={handleLogin} />}
        {user === 'admin' && <AdminDashboard onLogout={handleLogout} />}
        {user === 'student' && <StudentDashboard onLogout={handleLogout} />}
      </main>
      
      {/* Required Signature */}
      <footer className="bg-white border-t py-4 text-center text-sm text-gray-500 shadow-inner">
        structured by Pratham Amin
      </footer>
    </div>
  );
}
