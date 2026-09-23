import React, { useState } from 'react';

export default function AdminDashboard({ onLogout }) {
  const [sessionActive, setSessionActive] = useState(false);
  
  // Mock Database for students
  const [students, setStudents] = useState([
    { id: 'STU01', name: 'Aarav Patel', status: 'Absent' },
    { id: 'STU02', name: 'Rohan Sharma', status: 'Absent' },
    { id: 'STU03', name: 'Priya Singh', status: 'Absent' },
  ]);

  const toggleAttendance = (index) => {
    const newStudents = [...students];
    newStudents[index].status = newStudents[index].status === 'Absent' ? 'Present' : 'Absent';
    setStudents(newStudents);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8 bg-admin text-white p-6 rounded-xl shadow-lg">
        <div>
          <h2 className="text-2xl font-bold">Admin Portal // PIXEL</h2>
          <p className="text-gray-400 text-sm mt-1">Logged in as CR Administrator</p>
        </div>
        <button onClick={onLogout} className="bg-red-500 hover:bg-red-600 px-5 py-2 rounded-lg font-medium transition">
          Logout
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Session Control Panel */}
        <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 col-span-1">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Session Controls</h3>
          <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
            {sessionActive ? (
              <div className="text-center">
                <div className="w-32 h-32 bg-gray-200 mx-auto mb-4 flex items-center justify-center rounded-lg shadow-inner">
                  <span className="text-xs text-gray-500">[Dynamic QR Code]</span>
                </div>
                <p className="text-green-600 font-bold mb-4 animate-pulse">Scanning Active...</p>
                <button onClick={() => setSessionActive(false)} className="w-full bg-red-500 text-white py-2 rounded-lg font-semibold">Stop Session</button>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-gray-500 mb-4">No active session</p>
                <button onClick={() => setSessionActive(true)} className="w-full bg-green-500 text-white py-2 px-6 rounded-lg font-semibold shadow-md hover:bg-green-600 transition">Start Attendance Session</button>
              </div>
            )}
          </div>
        </div>

        {/* Student Roster & Manual Override */}
        <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 col-span-2">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Class Roster & Manual Override</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b bg-gray-50 text-gray-600">
                  <th className="py-3 px-4">Roll No</th>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">System Status</th>
                  <th className="py-3 px-4 text-right">Admin Action (Proxy)</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student, index) => (
                  <tr key={student.id} className="border-b hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-mono text-sm text-gray-600">{student.id}</td>
                    <td className="py-3 px-4 font-medium">{student.name}</td>
                    <td className="py-3 px-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${student.status === 'Present' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {student.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button 
                        onClick={() => toggleAttendance(index)}
                        className={`text-sm px-4 py-1.5 rounded-lg border transition ${student.status === 'Present' ? 'border-red-500 text-red-600 hover:bg-red-50' : 'border-green-500 text-green-600 hover:bg-green-50'}`}
                      >
                        Mark {student.status === 'Present' ? 'Absent' : 'Present'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

