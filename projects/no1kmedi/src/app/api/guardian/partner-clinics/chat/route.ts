/**
 * 파트너 한의원 챗봇 API
 */

import { NextRequest, NextResponse } from 'next/server'
import { generateClinicalText } from '@/lib/ai-provider'

const PARTNER_CLINICS: Record<string, any> = {
  'clinic-001': {
    name: '중앙 한의원',
    chatbot_config: {
      greeting: '안녕하세요! 중앙 한의원입니다. 무엇을 도와드릴까요?',
      faq: [
        {
          question: '예약은 어떻게 하나요?',
          answer: '전화(02-1234-5678) 또는 온라인 예약을 이용하실 수 있습니다.'
        }
      ],
      booking_info: '온라인 예약은 24시간 가능하며, 당일 예약은 전화로 문의해주세요.'
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { clinic_id, message, chat_history } = body

    if (!clinic_id || !message) {
      return NextResponse.json(
        { success: false, error: '한의원 ID와 메시지가 필요합니다.' },
        { status: 400 }
      )
    }

    const clinic = PARTNER_CLINICS[clinic_id]
    if (!clinic) {
      return NextResponse.json(
        { success: false, error: '한의원을 찾을 수 없습니다.' },
        { status: 404 }
      )
    }

    const context = `당신은 ${clinic.name}의 상담 안내 챗봇입니다.\n질문:${message}`

    const result = await generateClinicalText(
      {
        prompt: context,
        systemInstruction: `You are a clinical front-desk chatbot for ${clinic.name}. Do not provide diagnosis or treatment decisions. Answer in Korean when possible.`,
        model: 'gemini-1.5-flash',
        temperature: 0.7,
        maxOutputTokens: 1024,
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
    })
  } catch (error: any) {
    console.error('챗봇 오류:', error)
    return NextResponse.json(
      {
        success: false,
        error: `챗봇 응답 실패: ${error.message}`
      },
      { status: 500 }
    )
  }
}
