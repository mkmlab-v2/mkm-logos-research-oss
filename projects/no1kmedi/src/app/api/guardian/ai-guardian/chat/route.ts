/**
 * 임상 보조 가디언 채팅 API
 *
 * 진료 보조 AI와의 대화형 상담
 * 
 * 작성일: 2026-02-03
 * 공개 브랜드 도메인: jema-ai.com (가디언 채팅 API)
 * 상태: ✅ 구현 완료
 */

import { NextRequest, NextResponse } from 'next/server'
import { generateClinicalText } from '@/lib/ai-provider'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, health_data, chat_history } = body

    const extract4DVector = (healthData: any) => {
      if (healthData?.survey?.vector_4d) {
        return healthData.survey.vector_4d
      }
      return { S: 0.25, L: 0.25, K: 0.25, M: 0.25 }
    }

    const vector4d = extract4DVector(health_data)
    const vectorCoords = `${vector4d.S.toFixed(3)},${vector4d.L.toFixed(3)},${vector4d.K.toFixed(3)},${vector4d.M.toFixed(3)}`
    
    const hist = Array.isArray(chat_history) ? chat_history : []
    const recentHistory = hist.slice(-10).map((chat: { role?: string; message?: string }) =>
      `${chat.role === 'user' ? 'U' : 'A'}:${(chat.message || '').substring(0, 120)}`,
    ).join('|')

    const context = `no1kmedi clinical support assistant. 4D: [${vectorCoords}].
History: ${recentHistory || 'none'}
Q: ${message}
Theory: equilibrium reference, 0.25 target band.
Output: 2-3 sentences, pre-consultation clinical-support advice.`

    const result = await generateClinicalText(
      {
        prompt: context,
        systemInstruction:
          'You are the no1kmedi clinical support assistant for Korean medicine workflows. Do not diagnose. Answer in Korean when possible, with concise pre-consultation guidance based on S-L-K-M vectors.',
        model: 'gemini-2.5-flash',
        temperature: 0.7,
        maxOutputTokens: 2048,
        topP: 0.95,
        topK: 40,
      },
      'guardian_public_chat',
    )

    return NextResponse.json({
      success: true,
      response: result.text.trim(),
      meta: {
        provider: result.provider,
        fallback_used: result.fallbackUsed,
      },
    }, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      }
    })
  } catch (error: any) {
    console.error('임상 보조 가디언 채팅 오류:', error)
    return NextResponse.json(
      {
        success: false,
        error: `채팅 실패: ${error.message}`
      },
      { status: 500 }
    )
  }
}
