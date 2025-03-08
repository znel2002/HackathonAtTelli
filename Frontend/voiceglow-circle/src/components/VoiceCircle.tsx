
import React from "react";
import { cn } from "@/lib/utils";

type VoiceStatus = "idle" | "speaking" | "listening";

interface VoiceCircleProps {
  status: VoiceStatus;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const VoiceCircle: React.FC<VoiceCircleProps> = ({
  status,
  size = "md",
  className,
}) => {
  const sizes = {
    sm: {
      container: "w-16 h-16",
      inner: "w-12 h-12",
      outer: "w-16 h-16",
    },
    md: {
      container: "w-24 h-24",
      inner: "w-16 h-16",
      outer: "w-24 h-24",
    },
    lg: {
      container: "w-32 h-32",
      inner: "w-20 h-20",
      outer: "w-32 h-32",
    },
  };

  const getStatusClasses = (status: VoiceStatus) => {
    switch (status) {
      case "speaking":
        return {
          inner: "bg-red-600", // Tomato sauce red
          outer: "bg-red-600 animate-pulse-ring opacity-30",
        };
      case "listening":
        return {
          inner: "bg-amber-500", // Cheese yellow
          outer: "bg-amber-500 animate-pulse-ring opacity-30",
        };
      default:
        return {
          inner: "bg-stone-300", // Pizza crust color
          outer: "bg-stone-300 opacity-0",
        };
    }
  };

  const statusClasses = getStatusClasses(status);
  const sizeClasses = sizes[size];

  return (
    <div
      className={cn(
        "voice-circle",
        sizeClasses.container,
        className
      )}
    >
      {/* Outer pulse ring (animated when speaking/listening) */}
      <div
        className={cn(
          "voice-circle-pulse",
          sizeClasses.outer,
          statusClasses.outer,
          status !== "idle" ? "animate-pulse-ring" : ""
        )}
      />
      
      {/* Inner dot (changes color based on status) */}
      <div
        className={cn(
          "voice-circle-inner",
          sizeClasses.inner,
          statusClasses.inner,
          status !== "idle" ? "animate-pulse-dot" : ""
        )}
      />
    </div>
  );
};

export default VoiceCircle;
