/**
 * 임상 보조 가디언 API
 *
 * rPPG, 설진, 음성, 설문 데이터를 통합하여
 * 진료 보조 AI 상담 제공
 * 
 * 작성일: 2026-02-03
 * 도메인: no1kmedi.com/guardian
 * 상태: ✅ 구현 완료
 */

import { NextRequest, NextResponse } from 'next/server'
import { generateClinicalText } from '@/lib/ai-provider'

interface HealthData {
  rppg?: {
    heart_rate?: number
    stress_score?: number
    signal_quality?: number
  }
  tongue?: {
    color?: string
    coating?: string
    shape?: string
    moisture?: string
    hydrationScore?: number
    healthInsight?: string
  }
  voice?: {
    pitch?: number
    jitter?: number
    shimmer?: number
    hnr?: number
  }
  survey?: {
    vector_4d?: {
      S: number
      L: number
      K: number
      M: number
    }
    total_score?: number
    traffic_light?: {
      status: string
      risk_score: number
    }
  }
}

function convertTo4DVector(healthData: HealthData): { S: number; L: number; K: number; M: number } {
  let S = 0.25
  let L = 0.25
  let K = 0.25
  let M = 0.25

  if (healthData.survey?.vector_4d) {
    return healthData.survey.vector_4d
  }

  if (healthData.rppg) {
    const stress = healthData.rppg.stress_score || 50
    const heartRate = healthData.rppg.heart_rate || 70

    if (stress > 70) {
      S -= 0.1
      M += 0.1
    }

    if (heartRate < 60 || heartRate > 100) {
      M += 0.05
    }
  }

  if (healthData.tongue) {
    const hydration = healthData.tongue.hydrationScore || 50

    if (hydration < 50) {
      M += 0.05
    }

    if (healthData.tongue.color === 'Red' || healthData.tongue.color === 'Purple') {
      M += 0.05
    }
  }

  if (healthData.voice) {
    const jitter = healthData.voice.jitter || 0
    const shimmer = healthData.voice.shimmer || 0

    if (jitter > 0.5 || shimmer > 0.3) {
      S -= 0.05
    }
  }

  const sum = S + L + K + M
  return {
    S: Math.max(0, Math.min(1, S / sum)),
    L: Math.max(0, Math.min(1, L / sum)),
    K: Math.max(0, Math.min(1, K / sum)),
    M: Math.max(0, Math.min(1, M / sum))
  }
}

function calculateTrafficLight(vector4d: { S: number; L: number; K: number; M: number }): {
  status: 'high_risk' | 'caution' | 'normal'
  risk_score: number
  message: string
  icon: string
} {
  const riskScore = vector4d.M

  if (riskScore >= 0.7) {
    return {
      status: 'high_risk',
      risk_score: riskScore,
      message: '주의 신호가 높습니다. 가능한 빠르게 한의사 상담을 권장합니다.',
      icon: '🔴'
    }
  } else if (riskScore >= 0.5) {
    return {
      status: 'caution',
      risk_score: riskScore,
      message: '주의가 필요한 상태입니다. 생활 관리 점검과 상담 준비를 권장합니다.',
      icon: '🟡'
    }
  } else {
    return {
      status: 'normal',
      risk_score: riskScore,
      message: '현재 지표는 안정 범위입니다. 현재 관리 루틴을 유지해 보세요.',
      icon: '🟢'
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { health_data }: { health_data: HealthData } = body

    const vector4d = convertTo4DVector(health_data)
    const trafficLight = calculateTrafficLight(vector4d)

    const vectorCoords = `${vector4d.S.toFixed(3)},${vector4d.L.toFixed(3)},${vector4d.K.toFixed(3)},${vector4d.M.toFixed(3)}`
    const trafficStatus = trafficLight.status === 'high_risk' ? 'R' : trafficLight.status === 'caution' ? 'Y' : 'G'

    const prompt = `System: You are the no1kmedi clinical support assistant. Analyze the 4D vector [${vectorCoords}] and status ${trafficStatus}.
Context: S, L, K, M dimensions; target balance band 0.25.
Task: Provide concise clinical-support advice for pre-consultation (not a diagnosis).
Output JSON: {"message": "Direct, empathetic insight (2 sentences)", "recommendations": ["Actionable advice 1", "Actionable advice 2", "Actionable advice 3"]}`

    const result = await generateClinicalText({
      prompt,
      systemInstruction:
        'You are the no1kmedi clinical support assistant for Korean medicine workflows. You do not diagnose. Provide concise, empathetic pre-consultation guidance in Korean, based on 4D vector analysis (S-L-K-M).',
      model: 'gemini-1.5-flash',
      temperature: 0.7,
      maxOutputTokens: 2048,
      topP: 0.95,
      topK: 40,
    })

    const jsonStr = result.text.replace(/```json|```/g, '').trim()
    let aiAnalysis: { message: string; recommendations?: string[] }
    try {
      aiAnalysis = JSON.parse(jsonStr)
    } catch {
      aiAnalysis = {
        message: result.text.trim() || '상담 보조 응답을 생성했습니다. 자세한 내용은 상담 시 확인해 주세요.',
        recommendations: [
          '현재 증상과 생활 패턴을 정리해 상담 시 전달해 주세요.',
          '무리한 자가 판단보다 전문 상담 일정을 먼저 잡아 주세요.',
          '수면/식사/스트레스 지표를 3일 이상 기록해 오시면 도움이 됩니다.',
        ],
      }
    }

    return NextResponse.json({
      success: true,
      analysis: {
        status: trafficLight.status,
        message: aiAnalysis.message,
        recommendations: aiAnalysis.recommendations || [],
        vector_4d: vector4d,
        traffic_light: trafficLight,
        provider_meta: {
          provider: result.provider,
          fallback_used: result.fallbackUsed,
        },
      }
    })
  } catch (error: any) {
    console.error('임상 보조 가디언 오류:', error)
    return NextResponse.json(
      {
        success: false,
        error: `AI 보조 분석 실패: ${error.message}`
      },
      { status: 500 }
    )
  }
}
