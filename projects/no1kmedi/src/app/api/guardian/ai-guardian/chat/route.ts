/**
 * Clinical Copilot Guardian 채팅 API
 * 
 * 진료 보조 AI와의 대화형 상담
 * 
 * 작성일: 2026-02-03
 * 도메인: no1kmedi.com/guardian
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
    
    const recentHistory = chat_history.slice(-3).map((chat: any) => 
      `${chat.role === 'user' ? 'U' : 'A'}:${chat.message.substring(0, 50)}`
    ).join('|')

    const context = `Clinical Copilot Guardian. 4D: [${vectorCoords}]. 
History: ${recentHistory || 'none'}
Q: ${message}
Theory: 보명지주, 0.25 평형. 
Output: 2-3 sentences, pre-consultation clinical-support advice.`

    const result = await generateClinicalText({
      prompt: context,
      systemInstruction:
        'You are no1kmedi Clinical Copilot Guardian, a clinical-support assistant. Do not diagnose. Answer in Korean when possible, with concise and actionable pre-consultation guidance based on S-L-K-M vectors.',
      model: 'gemini-1.5-flash',
      temperature: 0.7,
      maxOutputTokens: 2048,
      topP: 0.95,
      topK: 40,
    })

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
    console.error('Clinical Copilot 채팅 오류:', error)
    return NextResponse.json(
      {
        success: false,
        error: `채팅 실패: ${error.message}`
      },
      { status: 500 }
    )
  }
}
