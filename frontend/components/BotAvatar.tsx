
import React from 'react';

export const BotAvatar: React.FC = () => {
  return (
    <div className="w-10 h-10 rounded-full flex items-center justify-center relative overflow-hidden bg-black text-white shadow-lg border-2 border-green-600">
      <i className="fa-solid fa-shield-halved text-lg z-10"></i>
      <div className="absolute top-0 w-full h-1/3 bg-black"></div>
      <div className="absolute top-1/3 w-full h-1/6 bg-red-600"></div>
      <div className="absolute bottom-0 w-full h-1/3 bg-green-700"></div>
    </div>
  );
};
