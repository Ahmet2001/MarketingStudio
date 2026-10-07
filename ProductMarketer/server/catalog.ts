export type ToolCategory = 'image' | 'video' | 'social'

export interface ToolDefinition {
  id: string
  title: string
  category: ToolCategory
  outputKind: 'image' | 'video' | 'carousel'
  provider: string
  model: string
  optionCount: number
  estimatedCostCents: number
}

export const toolCatalog: ToolDefinition[] = [
  { id: 'template-cover', title: 'Template cover generator', category: 'image', outputKind: 'image', provider: 'local', model: 'template-compositor-v1', optionCount: 4, estimatedCostCents: 0 },
  { id: 'ai-cover', title: 'AI cover generator', category: 'image', outputKind: 'image', provider: 'local', model: 'demo-image-v1', optionCount: 4, estimatedCostCents: 8 },
  { id: 'template-photo', title: 'Studio photo templates', category: 'image', outputKind: 'image', provider: 'local', model: 'template-compositor-v1', optionCount: 4, estimatedCostCents: 0 },
  { id: 'ai-photo', title: 'AI professional photos', category: 'image', outputKind: 'image', provider: 'local', model: 'demo-image-v1', optionCount: 4, estimatedCostCents: 10 },
  { id: 'social-thread', title: 'AI social thread', category: 'social', outputKind: 'carousel', provider: 'local', model: 'demo-story-v1', optionCount: 4, estimatedCostCents: 12 },
  { id: 'ugc-video', title: 'UGC video builder', category: 'video', outputKind: 'video', provider: 'local', model: 'demo-video-v1', optionCount: 4, estimatedCostCents: 40 },
  { id: 'artistic-motion', title: 'Artistic product motion', category: 'video', outputKind: 'video', provider: 'local', model: 'demo-video-v1', optionCount: 4, estimatedCostCents: 30 },
  { id: 'explainer', title: 'Product explainer', category: 'video', outputKind: 'video', provider: 'local', model: 'demo-video-v1', optionCount: 4, estimatedCostCents: 32 },
  { id: 'demo-video', title: 'Product demo video', category: 'video', outputKind: 'video', provider: 'local', model: 'template-video-v1', optionCount: 4, estimatedCostCents: 15 },
  { id: 'spokesperson', title: 'AI spokesperson', category: 'video', outputKind: 'video', provider: 'local', model: 'demo-avatar-v1', optionCount: 4, estimatedCostCents: 45 },
  { id: 'unboxing', title: 'AI unboxing sequence', category: 'social', outputKind: 'carousel', provider: 'local', model: 'demo-story-v1', optionCount: 4, estimatedCostCents: 16 },
  { id: 'campaign-kit', title: 'Multi-format campaign kit', category: 'social', outputKind: 'carousel', provider: 'local', model: 'demo-campaign-v1', optionCount: 4, estimatedCostCents: 24 },
]

export const toolById = new Map(toolCatalog.map((tool) => [tool.id, tool]))
