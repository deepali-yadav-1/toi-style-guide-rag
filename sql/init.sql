create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  chunk_hash text not null unique,
  document_name text not null,
  page_number integer not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(1536) not null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists document_chunks_document_name_idx
  on document_chunks (document_name);

create index if not exists document_chunks_page_number_idx
  on document_chunks (page_number);

create index if not exists document_chunks_embedding_idx
  on document_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function match_document_chunks(
  query_embedding vector(1536),
  match_count integer default 6
)
returns table (
  id uuid,
  document_name text,
  page_number integer,
  chunk_index integer,
  content text,
  similarity double precision
)
language sql
as $$
  select
    document_chunks.id,
    document_chunks.document_name,
    document_chunks.page_number,
    document_chunks.chunk_index,
    document_chunks.content,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;
