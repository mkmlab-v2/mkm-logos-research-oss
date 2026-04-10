/**
 * Qdrant 벡터 검색 유틸리티
 * 
 * 목적: 논문 및 뉴스 검색을 위한 Qdrant 벡터 검색 함수
 * 사용: 채팅 API에서 RAG (Retrieval-Augmented Generation) 구현
 */

interface QdrantSearchResult {
  id: string | number
  score: number
  payload: {
    title?: string
    abstract?: string
    content?: string
    authors?: string[]
    year?: number
    url?: string
    doi?: string
    source?: string
    published_at?: string
    [key: string]: any
  }
}

interface SearchOptions {
  collection: string
  query: string
  topK?: number
  scoreThreshold?: number
  filter?: Record<string, any>
}

/**
 * Qdrant 벡터 검색 (HTTP API 직접 호출)
 * 
 * 참고: Qdrant는 REST API를 제공하므로, 임베딩 벡터를 생성한 후 검색 가능
 * 현재는 백엔드 API를 통해 검색 (임베딩 생성은 백엔드에서 처리)
 */
export async function searchQdrant(
  options: SearchOptions
): Promise<QdrantSearchResult[]> {
  const {
    collection,
    query,
    topK = 5,
    scoreThreshold = 0.3,
    filter
  } = options

  try {
    // 백엔드 API를 통해 Qdrant 검색 (임베딩 생성 포함)
    // 운영/복구 모두에서 명시적으로 엔드포인트를 고정할 수 있게 우선순위 추가
    const backendUrl =
      process.env.QDRANT_SEARCH_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000'
    
    const response = await fetch(
      `${backendUrl}/api/qdrant/search`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collection,
          query,
          top_k: topK,
          score_threshold: scoreThreshold,
          filter,
        }),
        // 타임아웃 설정 (10초)
        signal: AbortSignal.timeout(10000),
      }
    )

    if (!response.ok) {
      throw new Error(`Qdrant 검색 실패: ${response.statusText}`)
    }

    const data = await response.json()
    return data.results || []
  } catch (error) {
    console.error('Qdrant 검색 오류:', error)
    // 오류 발생 시 빈 배열 반환 (fallback)
    return []
  }
}

/**
 * 논문 검색 (Qdrant 벡터 검색)
 */
export async function searchPapers(
  query: string,
  options?: {
    topK?: number
    constitution?: string
    year?: number
  }
): Promise<QdrantSearchResult[]> {
  const { topK = 5, constitution, year } = options || {}

  const filter: Record<string, any> = {}
  if (constitution) {
    filter.constitution = constitution
  }
  if (year) {
    filter.year = year
  }

  return searchQdrant({
    collection: 'medical_papers_collection',
    query,
    topK,
    filter: Object.keys(filter).length > 0 ? filter : undefined,
  })
}

/**
 * 뉴스 검색 (Qdrant 벡터 검색)
 */
export async function searchNews(
  query: string,
  options?: {
    topK?: number
    days?: number // 최근 N일 이내 뉴스만
  }
): Promise<QdrantSearchResult[]> {
  const { topK = 3, days } = options || {}

  const filter: Record<string, any> = {}
  if (days) {
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - days)
    filter.published_at = {
      gte: cutoffDate.toISOString(),
    }
  }

  return searchQdrant({
    collection: 'news_collection',
    query,
    topK,
    filter: Object.keys(filter).length > 0 ? filter : undefined,
  })
}

/**
 * 검색 결과를 프롬프트 형식으로 변환
 */
export function formatSearchResultsForPrompt(
  results: QdrantSearchResult[],
  type: 'papers' | 'news' = 'papers'
): string {
  if (!results || results.length === 0) {
    return ''
  }

  const formatted = results.map((result, index) => {
    const { payload } = result
    const citation = `[${index + 1}]`
    
    if (type === 'papers') {
      const authors = Array.isArray(payload.authors) 
        ? payload.authors.join(', ') 
        : (payload.authors || '저자 미상')
      return `${citation} ${payload.title || '제목 없음'} (${payload.year || '연도 미상'}) - ${authors}\n   ${payload.abstract || payload.content || ''}`
    } else {
      const dateStr = payload.published_at 
        ? new Date(payload.published_at).toLocaleDateString('ko-KR') 
        : '날짜 미상'
      return `${citation} ${payload.title || '제목 없음'} - ${payload.source || '출처 미상'} (${dateStr})\n   ${payload.content || ''}`
    }
  }).join('\n\n')

  return formatted
}

/**
 * 검색 결과를 소스 인용 형식으로 변환
 */
export function formatCitations(
  results: QdrantSearchResult[]
): Array<{
  id: number
  title: string
  url?: string
  year?: number
  doi?: string
  journal?: string
  source?: string
  published_at?: string
}> {
  if (!results || results.length === 0) {
    return []
  }
  
  return results.map((result, index) => ({
    id: index + 1,
    title: result.payload?.title || '제목 없음',
    url: result.payload?.url,
    year: result.payload?.year,
    doi: result.payload?.doi,
    journal: result.payload?.journal,
    source: result.payload?.source,
    published_at: result.payload?.published_at,
  }))
}

