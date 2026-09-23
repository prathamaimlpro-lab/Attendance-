import React, { useState } from 'react';

export default function StudentDashboard({ onLogout }) {
  const [attendanceMarked, setAttendanceMarked] = useState(false);

  const handleScanMock = () => {
    alert("Simulating Camera QR Scan & GPS Geolocation check...");
    setAttendanceMarked(true);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8 bg-primary text-white p-6 rounded-xl shadow-lg">
        <div>
          <h2 className="text-2xl font-bold">Student Portal // PIXEL</h2>
          <p className="text-indigo-200 text-sm mt-1">Welcome back, Student</p>
        </div>
        <button onClick={onLogout} className="bg-indigo-800 hover:bg-indigo-900 px-5 py-2 rounded-lg font-medium transition shadow-inner">
          Logout
        </button>
      </div>

      <div className="bg-white p-8 rounded-xl shadow-md border border-gray-100 text-center flex flex-col items-center justify-center min-h-[400px]">
        {attendanceMarked ? (
          <div className="space-y-4">
            <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto text-4xl shadow-inner">
              ✓
            </div>
            <h3 className="text-2xl font-bold text-gray-800">Attendance Marked!</h3>
            <p className="text-gray-500">Your location and scan have been verified.</p>
          </div>
        ) : (
          <div className="space-y-6 w-full max-w-md">
            <h3 className="text-xl font-semibold text-gray-800">Today's Session</h3>
            <p className="text-gray-500 text-sm">Please ensure you are inside the classroom and connected to the campus network.</p>
            
            <div className="p-6 border-2 border-dashed border-primary rounded-xl bg-indigo-50">
               <button 
                onClick={handleScanMock}
                className="w-full bg-primary hover:bg-indigo-700 text-white font-bold py-4 rounded-xl transition shadow-lg text-lg flex items-center justify-center gap-2"
              >
                📷 Scan Admin QR Code
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

