import { useRef, useEffect, useCallback } from 'react';
import { animate } from 'framer-motion';

/**
 * Fluid drawer/sheet hook with spring-based motion, velocity handoff, and rubber-banding
 * Based on Apple's "Designing Fluid Interfaces" principles
 */
export function useDragSheet({
  isOpen,
  onClose,
  direction = 'right', // 'right' | 'left' | 'bottom'
  width = 420,
  reducedMotion = false,
}) {
  const elementRef = useRef(null);
  const animationRef = useRef(null);
  const dragStateRef = useRef({
    isDragging: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    velocityX: 0,
    velocityY: 0,
    lastTime: 0,
    lastX: 0,
    lastY: 0,
  });

  // Spring configurations
  const SPRING_CONFIG = {
    default: { type: 'spring', stiffness: 300, damping: 30, mass: 1 },      // Critically damped
    momentum: { type: 'spring', stiffness: 300, damping: 22, mass: 1 },     // Slight bounce for momentum
    gentle: { type: 'spring', stiffness: 200, damping: 30, mass: 1 },       // Gentle settle
  };

  const RUBBER_BAND_CONSTANT = 0.55;
  const DISMISS_THRESHOLD = 0.35; // 35% of width/height
  const MIN_VELOCITY_TO_DISMISS = 500; // px/s

  const getTransform = useCallback((x, y) => {
    if (direction === 'right') return `translateX(${x}px)`;
    if (direction === 'left') return `translateX(${x}px)`;
    return `translateY(${y}px)`;
  }, [direction]);

  const getTargetPosition = useCallback(() => {
    if (direction === 'right') return width;
    if (direction === 'left') return -width;
    return window.innerHeight;
  }, [direction, width]);

  const rubberBand = useCallback((overshoot, dimension) => {
    const constant = RUBBER_BAND_CONSTANT;
    return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
  }, []);

  const animateTo = useCallback((targetX, targetY, config, initialVelocity = 0) => {
    const el = elementRef.current;
    if (!el) return;

    // Cancel any ongoing animation
    if (animationRef.current) {
      animationRef.current.stop();
    }

    const transform = getTransform(targetX, targetY);

    animationRef.current = animate(
      el,
      { transform },
      {
        ...config,
        velocity: initialVelocity,
        onComplete: () => {
          animationRef.current = null;
        },
      }
    );
  }, [getTransform]);

  const snapToClosed = useCallback((velocity = 0) => {
    animateTo(0, 0, SPRING_CONFIG.momentum, velocity);
  }, [animateTo]);

  const snapToOpen = useCallback((velocity = 0) => {
    const target = getTargetPosition();
    const x = direction === 'right' ? target : direction === 'left' ? -target : 0;
    const y = direction === 'bottom' ? target : 0;
    animateTo(x, y, SPRING_CONFIG.momentum, velocity);
  }, [animateTo, getTargetPosition, direction]);

  const handlePointerDown = useCallback((event) => {
    if (reducedMotion) return;
    if (event.button !== 0) return; // Only left click / primary touch

    const el = elementRef.current;
    if (!el) return;

    // Check if the click is on the drag handle or panel content (not on interactive elements)
    const target = event.target;
    if (target.closest('button, a, input, textarea, select, [role="button"]')) return;

    dragStateRef.current = {
      isDragging: true,
      startX: event.clientX,
      startY: event.clientY,
      currentX: 0,
      currentY: 0,
      velocityX: 0,
      velocityY: 0,
      lastTime: performance.now(),
      lastX: event.clientX,
      lastY: event.clientY,
    };

    el.setPointerCapture(event.pointerId);

    // Cancel any ongoing animation
    if (animationRef.current) {
      animationRef.current.stop();
      animationRef.current = null;
    }
  }, [reducedMotion]);

  const handlePointerMove = useCallback((event) => {
    const state = dragStateRef.current;
    if (!state.isDragging) return;

    const now = performance.now();
    const dt = (now - state.lastTime) / 1000; // seconds

    const deltaX = event.clientX - state.startX;
    const deltaY = event.clientY - state.startY;

    // Calculate velocity (exponential moving average)
    if (dt > 0) {
      const instantVX = (event.clientX - state.lastX) / dt;
      const instantVY = (event.clientY - state.lastY) / dt;
      state.velocityX = state.velocityX * 0.7 + instantVX * 0.3;
      state.velocityY = state.velocityY * 0.7 + instantVY * 0.3;
    }

    state.currentX = deltaX;
    state.currentY = deltaY;
    state.lastTime = now;
    state.lastX = event.clientX;
    state.lastY = event.clientY;

    // Apply rubber-banding resistance when dragging past edges
    let constrainedX = deltaX;
    let constrainedY = deltaY;

    if (direction === 'right') {
      // Dragging left (negative) closes, dragging right (positive) resists
      if (deltaX > 0) {
        constrainedX = rubberBand(deltaX, width);
      }
    } else if (direction === 'left') {
      // Dragging right (positive) closes, dragging left (negative) resists
      if (deltaX < 0) {
        constrainedX = -rubberBand(-deltaX, width);
      }
    } else if (direction === 'bottom') {
      // Dragging up (negative) closes, dragging down (positive) resists
      if (deltaY > 0) {
        constrainedY = rubberBand(deltaY, window.innerHeight);
      }
    }

    const el = elementRef.current;
    if (el) {
      el.style.transform = getTransform(constrainedX, constrainedY);
      el.style.transition = 'none';
    }
  }, [direction, width, getTransform]);

  const handlePointerUp = useCallback((event) => {
    const state = dragStateRef.current;
    if (!state.isDragging) return;

    state.isDragging = false;

    const el = elementRef.current;
    if (el) {
      el.releasePointerCapture(event.pointerId);
    }

    const { currentX, currentY, velocityX, velocityY } = state;
    const targetPos = getTargetPosition();
    const threshold = targetPos * DISMISS_THRESHOLD;

    // Determine primary velocity based on direction
    const primaryVelocity = direction === 'bottom' ? velocityY : velocityX;
    const primaryDelta = direction === 'bottom' ? currentY : currentX;

    // Decide: dismiss or snap back
    const shouldDismiss =
      Math.abs(primaryDelta) > threshold ||
      (Math.abs(primaryVelocity) > MIN_VELOCITY_TO_DISMISS && Math.sign(primaryVelocity) === Math.sign(primaryDelta));

    if (shouldDismiss) {
      onClose();
    } else {
      snapToOpen(primaryVelocity);
    }

    // Reset drag state
    dragStateRef.current = {
      isDragging: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
      velocityX: 0,
      velocityY: 0,
      lastTime: 0,
      lastX: 0,
      lastY: 0,
    };
  }, [direction, getTargetPosition, onClose, snapToOpen]);

  // Set up pointer events when mounted
  useEffect(() => {
    const el = elementRef.current;
    if (!el) return;

    el.addEventListener('pointerdown', handlePointerDown);
    el.addEventListener('pointermove', handlePointerMove);
    el.addEventListener('pointerup', handlePointerUp);
    el.addEventListener('pointercancel', handlePointerUp);
    el.addEventListener('pointerleave', handlePointerUp);

    return () => {
      el.removeEventListener('pointerdown', handlePointerDown);
      el.removeEventListener('pointermove', handlePointerMove);
      el.removeEventListener('pointerup', handlePointerUp);
      el.removeEventListener('pointercancel', handlePointerUp);
      el.removeEventListener('pointerleave', handlePointerUp);
    };
  }, [handlePointerDown, handlePointerMove, handlePointerUp]);

  // Animate on open/close prop changes
  useEffect(() => {
    if (reducedMotion) {
      const el = elementRef.current;
      if (el) {
        el.style.transition = 'transform 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        const target = isOpen ? getTargetPosition() : 0;
        const x = direction === 'right' ? target : direction === 'left' ? -target : 0;
        const y = direction === 'bottom' ? target : 0;
        el.style.transform = getTransform(x, y);
      }
      return;
    }

    if (isOpen) {
      snapToOpen();
    } else {
      snapToClosed();
    }
  }, [isOpen, reducedMotion, direction, getTargetPosition, snapToOpen, snapToClosed, getTransform]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        animationRef.current.stop();
      }
    };
  }, []);

  return {
    ref: elementRef,
    style: {
      transform: getTransform(0, 0),
      willChange: 'transform',
    },
  };
}