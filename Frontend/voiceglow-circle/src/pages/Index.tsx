
import React from "react";
import VoiceAgent from "@/components/VoiceAgent";

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-amber-50 to-red-100 p-4">
      <div className="w-full max-w-2xl mx-auto">
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl font-bold tracking-tight mb-2 text-red-600">Pizza Assistant</h1>
          <p className="text-stone-700">
            Order your perfect pizza with voice or text 🍕
          </p>
        </div>
        
        <div className="bg-white/30 backdrop-blur-md rounded-xl p-8 shadow-sm border border-orange-200 animate-scale-in">
          <VoiceAgent />
        </div>
      </div>
    </div>
  );
};

export default Index;
