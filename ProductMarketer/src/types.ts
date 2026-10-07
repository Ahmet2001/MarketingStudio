export type PageId =
  | 'overview'
  | 'new-project'
  | 'generate'
  | 'projects'
  | 'videos'
  | 'library'
  | 'insights'
  | 'competitors'
  | 'integrations'
  | 'models'
  | 'profile'
  | 'settings'
  | 'editor'

export type CreativeVariant = 'citrus' | 'lavender' | 'midnight' | 'sand'

export interface Creative {
  id: number
  title: string
  headline: string
  subline: string
  cta: string
  score: number
  format: string
  variant: CreativeVariant
  status?: 'ready' | 'draft'
}

export interface CampaignProject {
  id: number
  name: string
  type: string
  outputs: number
  updated: string
  status: 'Ready' | 'Draft'
  variant: CreativeVariant
}
