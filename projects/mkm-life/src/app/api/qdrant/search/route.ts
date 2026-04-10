import { NextRequest, NextResponse } from 'next/server'

type SearchBody = {
  collection?: string
  query?: string
  top_k?: number
  score_threshold?: number
}

const FALLBACK_ENABLED = (process.env.QDRANT_FALLBACK_ENABLED || '1').trim() !== '0'

function decodeXml(value: string): string {
  return value
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

function curatedFallbackPapers() {
  return [
    {
      id: 'fallback-1',
      score: 0.78,
      payload: {
        title: 'Lifestyle interventions for hypertension prevention and control',
        abstract:
          'Exercise, sodium reduction, and sleep hygiene are consistently associated with improved blood pressure outcomes.',
        authors: ['Whelton PK', 'Carey RM'],
        year: 2018,
        url: 'https://pubmed.ncbi.nlm.nih.gov/30280368/',
        source: 'fallback_curated',
      },
    },
    {
      id: 'fallback-2',
      score: 0.73,
      payload: {
        title: 'Sleep duration and blood pressure: systematic review',
        abstract:
          'Insufficient sleep is associated with elevated blood pressure and cardiometabolic risk in adults.',
        authors: ['Cappuccio FP', 'Miller MA'],
        year: 2017,
        url: 'https://pubmed.ncbi.nlm.nih.gov/28162122/',
        source: 'fallback_curated',
      },
    },
  ]
}

function buildPubmedQuery(rawQuery: string): string {
  const q = rawQuery.toLowerCase()
  const terms = new Set<string>([rawQuery.trim()])

  const keywordMap: Array<[RegExp, string]> = [
    [/(수면|불면|잠)/, 'sleep quality'],
    [/(혈압|고혈압)/, 'hypertension'],
    [/(스트레스)/, 'stress management'],
    [/(피로|만성 피로)/, 'fatigue'],
    [/(운동|걷기)/, 'physical activity'],
    [/(식단|당분|비만)/, 'diet lifestyle'],
    [/(두통)/, 'headache management'],
    [/(카페인)/, 'caffeine reduction'],
    [/(면역)/, 'immune health'],
    [/(집중력)/, 'cognitive performance'],
    [/(장 건강)/, 'gut microbiome health'],
    [/(눈 피로)/, 'digital eye strain'],
  ]

  for (const [pattern, englishTerm] of keywordMap) {
    if (pattern.test(q)) {
      terms.add(englishTerm)
    }
  }

  // 한글 질문은 기본 공중보건 키워드를 추가해 PubMed hit 확률을 높인다.
  if (/[가-힣]/.test(rawQuery)) {
    terms.add('lifestyle intervention')
    terms.add('preventive health')
  }

  return Array.from(terms)
    .map((term) => `(${term})`)
    .join(' OR ')
}

function extractDoiFromSummaryItem(item: any): string | undefined {
  const articleIds = Array.isArray(item?.articleids) ? item.articleids : []
  const doiFromArray = articleIds.find((a: any) => {
    const type = String(a?.idtype || '').toLowerCase()
    return type === 'doi'
  })?.value
  if (doiFromArray) return String(doiFromArray)

  const elocation = String(item?.elocationid || '')
  const doiMatch = elocation.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i)
  if (doiMatch?.[0]) return doiMatch[0]
  return undefined
}

function curatedFallbackNews() {
  const now = new Date().toISOString()
  return [
    {
      id: 'news-fallback-1',
      score: 0.71,
      payload: {
        title: 'WHO highlights sleep and blood pressure prevention guidance',
        content:
          'Global public-health guidance emphasizes sleep hygiene, sodium control, and regular activity for blood-pressure risk reduction.',
        source: 'who_fallback',
        published_at: now,
        url: 'https://www.who.int/news-room/fact-sheets/detail/hypertension',
      },
    },
    {
      id: 'news-fallback-2',
      score: 0.68,
      payload: {
        title: 'CDC lifestyle recommendations for heart and blood pressure health',
        content:
          'CDC prevention recommendations include exercise, weight management, smoking cessation, and sleep quality.',
        source: 'cdc_fallback',
        published_at: now,
        url: 'https://www.cdc.gov/bloodpressure/prevent.htm',
      },
    },
  ]
}

async function searchGoogleNewsRss(query: string, topK: number) {
  const rssUrl = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=ko&gl=KR&ceid=KR:ko`
  const response = await fetch(rssUrl, {
    headers: {
      'User-Agent': 'mkm-life-news-fallback/1.0',
      Accept: 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8',
    },
    signal: AbortSignal.timeout(8000),
  })
  if (!response.ok) return []
  const xml = await response.text()
  const items = xml.match(/<item>[\s\S]*?<\/item>/g) || []
  return items.slice(0, topK).map((item, idx) => {
    const title = decodeXml(item.match(/<title><!\[CDATA\[([\s\S]*?)\]\]><\/title>/)?.[1] || item.match(/<title>([\s\S]*?)<\/title>/)?.[1] || '제목 없음').trim()
    const link = decodeXml(item.match(/<link>([\s\S]*?)<\/link>/)?.[1] || '')
    const pubDateRaw = item.match(/<pubDate>([\s\S]*?)<\/pubDate>/)?.[1]
    const source = decodeXml(item.match(/<source[^>]*>([\s\S]*?)<\/source>/)?.[1] || 'google_news_rss')
    const description = decodeXml(item.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/)?.[1] || item.match(/<description>([\s\S]*?)<\/description>/)?.[1] || '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
    const publishedAt = pubDateRaw ? new Date(pubDateRaw).toISOString() : undefined

    return {
      id: `news-rss-${idx + 1}`,
      score: Math.max(0.35, 0.9 - idx * 0.08),
      payload: {
        title,
        content: description || title,
        source,
        published_at: publishedAt,
        url: link,
      },
    }
  })
}

/**
 * Local recovery endpoint for `/api/qdrant/search`.
 * - `medical_papers_collection`: PubMed E-utilities 기반 검색
 * - `news_collection`: Google News RSS 우선 + 실패 시 curated fallback
 */
export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SearchBody
    const collection = String(body.collection || '').trim()
    const query = String(body.query || '').trim()
    const topK = Math.max(1, Math.min(Number(body.top_k || 5), 10))

    if (!collection || !query) {
      return NextResponse.json({ results: [] })
    }

    if (collection === 'news_collection') {
      const rssResults = await searchGoogleNewsRss(query, topK)
      if (rssResults.length > 0) {
        return NextResponse.json({ results: rssResults })
      }
      return NextResponse.json({
        results: FALLBACK_ENABLED ? curatedFallbackNews().slice(0, topK) : [],
      })
    }

    // medical_papers_collection (fallback): PubMed 검색
    if (collection === 'medical_papers_collection') {
      const pubmedQuery = buildPubmedQuery(query)
      const esearchUrl =
        `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` +
        `?db=pubmed&term=${encodeURIComponent(pubmedQuery)}&retmax=${topK}&retmode=json&sort=relevance`
      const esearchRes = await fetch(esearchUrl)
      if (!esearchRes.ok) {
        return NextResponse.json({ results: [] })
      }

      const esearchData = (await esearchRes.json()) as {
        esearchresult?: { idlist?: string[] }
      }
      const ids = esearchData.esearchresult?.idlist || []
      if (ids.length === 0) {
        return NextResponse.json({
          results: FALLBACK_ENABLED ? curatedFallbackPapers().slice(0, topK) : [],
        })
      }

      const esummaryUrl =
        `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi` +
        `?db=pubmed&id=${ids.join(',')}&retmode=json`
      const esummaryRes = await fetch(esummaryUrl)
      if (!esummaryRes.ok) {
        return NextResponse.json({ results: [] })
      }

      const esummaryData = (await esummaryRes.json()) as {
        result?: Record<string, any>
      }

      const results = ids
        .map((pmid, idx) => {
          const item = esummaryData.result?.[pmid]
          if (!item) return null
          const authors = Array.isArray(item.authors)
            ? item.authors.map((a: any) => a?.name).filter(Boolean)
            : []
          return {
            id: pmid,
            score: Math.max(0.3, 0.95 - idx * 0.08),
            payload: {
              title: item.title || '제목 없음',
              abstract: item.sorttitle || item.title || '',
              authors,
              year: Number(String(item.pubdate || '').slice(0, 4)) || undefined,
              published_at: item.pubdate || undefined,
              journal: item.fulljournalname || item.source || undefined,
              url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
              doi: extractDoiFromSummaryItem(item),
              source: 'pubmed_fallback',
            },
          }
        })
        .filter(Boolean)

      if (results.length === 0) {
        return NextResponse.json({
          results: FALLBACK_ENABLED ? curatedFallbackPapers().slice(0, topK) : [],
        })
      }

      return NextResponse.json({ results })
    }

    return NextResponse.json({ results: [] })
  } catch (error) {
    console.error('qdrant search fallback route error:', error)
    return NextResponse.json({ results: [] })
  }
}
