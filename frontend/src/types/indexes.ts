export interface IndexCollectionStatus {
  name: string
  count: number
  status: string
}

export interface IndexStatus {
  milvus_db_path: string
  knowledge_dir: string
  log_dir: string
  collections: IndexCollectionStatus[]
}
