import { useStore } from '@nanostores/react'
import { type RefObject, useCallback, useLayoutEffect, useRef, useState } from 'react'

import { usePaneVisible } from '@/components/pane-shell/pane-visibility'
import { useResizeObserver } from '@/hooks/use-resize-observer'
import { triggerHaptic } from '@/lib/haptics'
import {
  $composerPopoutPosition,
  $composerPoppedOut,
  clampPopoutPosition,
  popoutBoundsElement,
  type PopoutPosition,
  readPopoutBounds,
  setComposerPoppedOut
} from '@/store/composer-popout'
import { isSecondaryWindow } from '@/store/windows'

import { useComposerPopoutGestures } from './use-popout-drag'

interface UseComposerPopoutOptions {
  composerRef: RefObject<HTMLFormElement | null>
}

/**
 * This surface's on-screen placement, derived from the shared drag intent.
 *
 * The atom is one value for the whole window — dragging the composer in any tab
 * moves it in all of them. But each chat surface owns a different rect (the
 * primary, a tile beside it, a background tab in the same stack), so the same
 * intent has to be clamped per surface. Clamping into the atom instead would
 * have every keep-alive-mounted tab overwrite the others with a position
 * bounded by ITS geometry, and the last one to run would win — which is exactly
 * how a drag in one tab used to get lost in another.
 *
 * While THIS surface is dragging, the gesture already clamped against this
 * rect, so the intent is the placement — re-deriving would only add a forced
 * reflow per frame.
 *
 * An inactive tab skips re-placing entirely and catches up on reveal: it stays
 * mounted (keep-alive), so a live drag would otherwise force a reflow in every
 * background tab on every frame.
 */
function usePopoutPlacement(
  composerRef: RefObject<HTMLFormElement | null>,
  intent: PopoutPosition,
  dragging: boolean,
  poppedOut: boolean
): PopoutPosition {
  const [placement, setPlacement] = useState(intent)
  const visible = usePaneVisible()
  // Re-place while this surface is the visible tab and isn't itself dragging.
  const live = poppedOut && visible && !dragging

  // Resolved before the shared ResizeObserver below registers (hook order puts
  // this layout effect first), so the observer always has this surface's own
  // bounds element rather than a document-wide first match.
  const boundsRef = useRef<Element | null>(null)

  useLayoutEffect(() => {
    boundsRef.current = popoutBoundsElement(composerRef.current)
  })

  const reclamp = useCallback(() => {
    const el = composerRef.current

    if (!el) {
      return
    }

    const size = { height: el.offsetHeight, width: el.offsetWidth }
    const next = clampPopoutPosition($composerPopoutPosition.get(), size, readPopoutBounds(el))

    // Bail on an unchanged placement: a sash drag resizes the surface every
    // frame, and a fresh object each time re-renders the whole composer.
    setPlacement(prev => (prev.bottom === next.bottom && prev.right === next.right ? prev : next))
  }, [composerRef])

  // The surface resizing (sash drag, sidebar open, tab split) re-places the box
  // against its new rect; the composer resizing (a growing draft) re-places it
  // against its new height.
  useResizeObserver(
    useCallback(() => {
      if (live) {
        reclamp()
      }
    }, [live, reclamp]),
    composerRef,
    boundsRef
  )

  // useLayoutEffect, not useEffect: a tab revealed after the box was dragged in
  // another one must not paint a frame at its stale placement before catching
  // up. Runs before paint, and no-ops for hidden tabs (`live`).
  useLayoutEffect(() => {
    if (!live) {
      return undefined
    }

    reclamp()
    // A second pass after layout settles (sidebar widths, fonts): anyone
    // restored out of bounds is pulled back even if the first measure was
    // premature.
    const raf = requestAnimationFrame(reclamp)
    window.addEventListener('resize', reclamp)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', reclamp)
    }
  }, [intent, live, reclamp])

  return dragging ? intent : placement
}

/**
 * Pop-out engine: the docked↔floating state (a shared, persisted atom), the
 * dock/float/toggle actions, the drag gestures, and this surface's placement.
 * Every chat surface participates — the primary thread, a session tile, a tab
 * in a stack — so the floating composer follows you across tabs and splits
 * instead of only existing in the main one.
 *
 * Secondary windows (the tiny Ctrl+Shift+N window, subagent watch windows) stay
 * docked: a floating composer makes no sense in a scratch window, and the
 * shared atom would yank it out of the main window's control.
 */
export function useComposerPopout({ composerRef }: UseComposerPopoutOptions) {
  const popoutAllowed = !isSecondaryWindow()
  const poppedOut = useStore($composerPoppedOut) && popoutAllowed
  const popoutIntent = useStore($composerPopoutPosition)

  const handleComposerPopOut = useCallback(() => {
    triggerHaptic('open')
    setComposerPoppedOut(true)
  }, [])

  const handleComposerDock = useCallback(() => {
    triggerHaptic('success')
    setComposerPoppedOut(false)
  }, [])

  // Double-click the grab area toggles dock/float. Undocking restores the last
  // position (the persisted atom is never cleared on dock).
  const handleComposerToggle = useCallback(() => {
    poppedOut ? handleComposerDock() : handleComposerPopOut()
  }, [handleComposerDock, handleComposerPopOut, poppedOut])

  const {
    dockProximity,
    dragging,
    onPointerDown: onComposerGesturePointerDown
  } = useComposerPopoutGestures({
    composerRef,
    onDock: handleComposerDock,
    onPopOut: handleComposerPopOut,
    poppedOut,
    position: popoutIntent
  })

  const popoutPosition = usePopoutPlacement(composerRef, popoutIntent, dragging, poppedOut)

  return {
    dockProximity,
    dragging,
    handleComposerToggle,
    onComposerGesturePointerDown,
    popoutAllowed,
    popoutPosition,
    poppedOut
  }
}
