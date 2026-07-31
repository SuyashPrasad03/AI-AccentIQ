/**
 * DropZone — Dashed-border upload/drop area
 * Used in: audio uploader, any future file upload surfaces
 *
 * @param {function} onDrop - Handler for dropped files
 * @param {function} onClick - Handler for click-to-browse
 * @param {boolean} [active] - Whether currently dragging over
 * @param {React.ReactNode} children - Content inside the drop zone
 * @param {string} [className] - Additional CSS classes
 */
import { useState, useCallback } from "react";

export function DropZone({ onDrop, onClick, active: controlledActive, children, className = "" }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const isActive = controlledActive ?? isDragOver;

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && onDrop) {
      onDrop(files);
    }
  }, [onDrop]);

  return (
    <div
      onClick={onClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
        transition-all duration-200
        ${isActive
          ? "border-primary bg-primary-soft scale-[1.01]"
          : "border-border hover:border-primary/50 hover:bg-bg-soft"
        }
        ${className}
      `}
      role="button"
      tabIndex={0}
      aria-label="Drop zone for file upload"
    >
      {children}
    </div>
  );
}
