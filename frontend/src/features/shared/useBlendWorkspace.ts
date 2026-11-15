import { useSyncExternalStore } from 'react'
import { getBlendWorkspace, subscribeBlendWorkspace } from '../../services/blendWorkspace'

export function useBlendWorkspace() {
  return useSyncExternalStore(subscribeBlendWorkspace, getBlendWorkspace)
}
