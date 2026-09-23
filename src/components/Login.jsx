import React, { useState } from 'react';

export default function Login({ onLogin }) {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Admin Login Check
    if (userId === 'admin' && password === 'pratham.3438') {
      onLogin('admin');
    } 
    // Mock Student Login Check (Any other ID starting with 'STU')
    else if (userId.toLowerCase().startsWith('stu') && password !== '') {
      onLogin('student');
    } 
    else {
      setError('Invalid Credentials. Use "admin" or a student ID (e.g., STU01).');
    }
  };

  return (
    <div className="min-h-[90vh] flex items-center justify-center">
      <div className="bg-white p-10 rounded-2xl shadow-xl w-96 border-t-4 border-primary">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-extrabold text-gray-800 tracking-tight">PIXEL</h1>
          <p className="text-gray-500 mt-2 text-sm">Attendance Management System</p>
        </div>
        
        {error && <div className="bg-red-100 text-red-600 p-3 rounded-lg text-sm mb-4">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700">Login ID</label>
            <input 
              type="text" 
              className="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none transition"
              placeholder="e.g. admin or STU01"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input 
              type="password" 
              className="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none transition"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button 
            type="submit" 
            className="w-full bg-primary hover:bg-indigo-700 text-white font-bold py-3 rounded-lg transition shadow-md"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}

