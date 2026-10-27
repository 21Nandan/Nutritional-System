import { useEffect } from 'react';

export function useLockBodyScroll(isLocked = true) {
  useEffect(() => {
    if (!isLocked) return;

    const originalOverflow = document.body.style.overflow;
    const originalOverscroll = document.body.style.overscrollBehavior;

    document.body.style.overflow = 'hidden';
    document.body.style.overscrollBehavior = 'none';

    return () => {
      document.body.style.overflow = originalOverflow || '';
      document.body.style.overscrollBehavior = originalOverscroll || '';
    };
  }, [isLocked]);
}
