import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

interface ConfirmModalProps {
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * The app's one destructive-confirmation pattern (extracted from Team
 * Management's original "Remove team member?" modal). Anything that used to
 * reach for window.confirm() -- e.g. Quick Replies' delete flow -- should
 * use this instead, so every "are you sure you want to delete X" moment in
 * the app looks and behaves the same way.
 */
export function ConfirmModal({
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
    >
      <div
        className="bg-[var(--color-bg-surface)] w-full max-w-sm rounded-xl shadow-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-[var(--color-text-primary)] mb-2">{title}</h2>
        <div className="text-sm text-[var(--color-text-secondary)] mb-6">{description}</div>
        <div className="flex justify-end space-x-3">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            className="min-w-[88px] border border-black text-[var(--color-text-primary)] hover:bg-gray-50 focus:border-[var(--color-brand-primary)] active:border-[var(--color-brand-primary)] focus:ring-[var(--color-brand-primary)]"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirm}
            className="min-w-[88px]"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );

  if (!mounted || typeof document === 'undefined') {
    return null;
  }

  return createPortal(modalContent, document.body);
}
