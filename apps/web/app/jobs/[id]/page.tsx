'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navigation } from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { ArrowLeft, RefreshCw, Upload, CheckCircle2, AlertCircle, MessageCircle, Send } from 'lucide-react'

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const jobId = parseInt(params.id)

  const [job, setJob] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [pushing, setPushing] = useState(false)
  const [pushSuccess, setPushSuccess] = useState(false)
  
  // Q&A State
  const [question, setQuestion] = useState('')
  const [qaHistory, setQaHistory] = useState<Array<{ question: string; answer: string }>>([])
  const [askingQuestion, setAskingQuestion] = useState(false)

  useEffect(() => {
    const apiKey = localStorage.getItem('apiKey')
    if (!apiKey) {
      router.push('/login')
      return
    }
    fetchJob()
  }, [])

  useEffect(() => {
    // Auto-refresh if job is still processing
    if (job && ['queued', 'converting', 'transcribing', 'extracting'].includes(job.status)) {
      const timer = setTimeout(() => {
        fetchJob(true)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [job])

  const fetchJob = async (silent = false) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const result = await api.getJob(jobId)
      setJob(result)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch job')
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const handlePush = async () => {
    setPushing(true)
    setError('')
    setPushSuccess(false)
    try {
      await api.pushToKommo(jobId)
      setPushSuccess(true)
      fetchJob(true)
    } catch (err: any) {
      setError(err.message || 'Push failed')
    } finally {
      setPushing(false)
    }
  }
  
  const handleAskQuestion = async () => {
    if (!question.trim()) return
    
    setAskingQuestion(true)
    try {
      const result = await api.askQuestion(jobId, question)
      setQaHistory([...qaHistory, { question: result.question, answer: result.answer }])
      setQuestion('') // Clear input
    } catch (err: any) {
      setError(err.message || 'Failed to ask question')
    } finally {
      setAskingQuestion(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: any; icon: any }> = {
      queued: { variant: 'secondary', icon: null },
      converting: { variant: 'secondary', icon: RefreshCw },
      transcribing: { variant: 'secondary', icon: RefreshCw },
      extracting: { variant: 'secondary', icon: RefreshCw },
      ready: { variant: 'default', icon: CheckCircle2 },
      failed: { variant: 'destructive', icon: AlertCircle },
      pushed: { variant: 'default', icon: Upload },
    }
    const config = variants[status] || variants.queued
    const Icon = config.icon
    return (
      <Badge variant={config.variant}>
        {Icon && <Icon className="h-3 w-3 mr-1 inline animate-spin" />}
        {status.toUpperCase()}
      </Badge>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">Loading...</div>
        </div>
      </div>
    )
  }

  if (error && !job) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="container mx-auto px-4 py-8">
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="container mx-auto px-4 py-8">
        <div className="mb-4">
          <Link href={`/leads/${job?.lead_id}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Lead
            </Button>
          </Link>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Job #{jobId}</CardTitle>
                  <CardDescription>
                    Created {job?.created_at ? formatDate(job.created_at) : 'N/A'}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(job?.status)}
                  <Button variant="outline" size="sm" onClick={() => fetchJob()}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-muted-foreground">Progress</p>
                  <p className="font-medium">{job?.progress_step || 'Queued'}</p>
                </div>
                {job?.last_error && (
                  <div className="bg-destructive/10 text-destructive px-4 py-3 rounded text-sm">
                    {job.last_error}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {job?.status === 'ready' && (
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <Button onClick={handlePush} disabled={pushing || job?.pushed_at}>
                  <Upload className="h-4 w-4 mr-2" />
                  {job?.pushed_at ? 'Already Pushed to Kommo' : 'Push to Kommo'}
                </Button>
                {pushSuccess && (
                  <p className="text-sm text-green-600 mt-2">Successfully pushed to Kommo!</p>
                )}
              </CardContent>
            </Card>
          )}

          {job?.status === 'ready' && (
            <Card>
              <CardHeader>
                <CardTitle>Results</CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="extraction">
                  <TabsList>
                    <TabsTrigger value="extraction">Extraction</TabsTrigger>
                    <TabsTrigger value="transcript">Transcript</TabsTrigger>
                    <TabsTrigger value="qa">💬 Ask Questions</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="extraction" className="space-y-4 mt-4">
                    {job?.extraction ? (
                      <div className="space-y-6">
                        {/* Summary */}
                        {job.extraction.call_summary && job.extraction.call_summary.length > 0 && (
                          <Card>
                            <CardContent className="pt-6">
                              <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                                📋 Резюме звонка
                              </h3>
                              <ul className="space-y-2">
                                {job.extraction.call_summary.map((item: string, i: number) => (
                                  <li key={i} className="flex items-start gap-2">
                                    <span className="text-primary mt-1">•</span>
                                    <span className="text-sm leading-relaxed">{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </CardContent>
                          </Card>
                        )}

                        {/* Concerns */}
                        {job.extraction.concerns && job.extraction.concerns.length > 0 && (
                          <div>
                            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                              ⚠️ Возражения и проблемы
                            </h3>
                            <div className="space-y-3">
                              {job.extraction.concerns.map((concern: any, i: number) => (
                                <Card key={i} className="border-l-4 border-l-red-500">
                                  <CardContent className="pt-4">
                                    <div className="flex items-start justify-between mb-3">
                                      <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="capitalize">
                                          {concern.type === 'pricing' ? '💰 Цена' : 
                                           concern.type === 'technical' ? '⚙️ Технические' :
                                           concern.type === 'competition' ? '🏆 Конкуренты' :
                                           concern.type === 'timeline' ? '⏰ Сроки' :
                                           concern.type === 'trust' ? '🤝 Доверие' : '📌 Другое'}
                                        </Badge>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        {[...Array(5)].map((_, idx) => (
                                          <span key={idx} className={idx < concern.severity ? 'text-red-500' : 'text-gray-300'}>
                                            ●
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                    <p className="text-sm leading-relaxed mb-3">{concern.detail}</p>
                                    {concern.evidence_quotes && concern.evidence_quotes.length > 0 && (
                                      <div className="bg-gray-50 p-3 rounded text-xs italic border-l-2 border-gray-300">
                                        {concern.evidence_quotes.map((quote: any, qi: number) => (
                                          <p key={qi}>"{quote.text}"</p>
                                        ))}
                                      </div>
                                    )}
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Next Steps */}
                        {job.extraction.next_steps && job.extraction.next_steps.length > 0 && (
                          <div>
                            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                              ✅ Следующие шаги
                            </h3>
                            <div className="space-y-2">
                              {job.extraction.next_steps.map((step: any, i: number) => (
                                <Card key={i} className="border-l-4 border-l-green-500">
                                  <CardContent className="pt-4">
                                    <div className="flex items-start gap-3">
                                      <span className="text-2xl">{i + 1}</span>
                                      <div className="flex-1">
                                        <p className="text-sm font-medium leading-relaxed mb-2">{step.action}</p>
                                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                          <span className="flex items-center gap-1">
                                            👤 <strong>{step.owner}</strong>
                                          </span>
                                          {step.suggested_due_days && (
                                            <span className="flex items-center gap-1">
                                              ⏱️ {step.suggested_due_days} {step.suggested_due_days === 1 ? 'день' : 'дней'}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Qualification */}
                        {job.extraction.qualification && (
                          <div>
                            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                              🎯 Квалификация лида
                            </h3>
                            <Card className="border-2">
                              <CardContent className="pt-6">
                                <div className="mb-6">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium">Готовность к покупке</span>
                                    <span className="text-2xl font-bold text-primary">
                                      {job.extraction.qualification.score}/100
                                    </span>
                                  </div>
                                  <div className="w-full bg-gray-200 rounded-full h-3">
                                    <div 
                                      className={`h-3 rounded-full transition-all ${
                                        job.extraction.qualification.score >= 80 ? 'bg-green-500' :
                                        job.extraction.qualification.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                      }`}
                                      style={{ width: `${job.extraction.qualification.score}%` }}
                                    />
                                  </div>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {job.extraction.qualification.score >= 80 ? '🔥 Горячий лид' :
                                     job.extraction.qualification.score >= 50 ? '🌡️ Теплый лид' : '❄️ Холодный лид'}
                                  </p>
                                </div>
                                
                                <div className="grid grid-cols-2 gap-4">
                                  <div className="bg-gray-50 p-3 rounded">
                                    <p className="text-xs text-muted-foreground mb-1">💰 Бюджет</p>
                                    <p className="text-sm font-medium">{job.extraction.qualification.budget || 'Неизвестен'}</p>
                                  </div>
                                  <div className="bg-gray-50 p-3 rounded">
                                    <p className="text-xs text-muted-foreground mb-1">⏰ Сроки</p>
                                    <p className="text-sm font-medium">{job.extraction.qualification.timeline || 'Неизвестны'}</p>
                                  </div>
                                  <div className="bg-gray-50 p-3 rounded col-span-2">
                                    <p className="text-xs text-muted-foreground mb-1">👔 Лицо принимающее решение</p>
                                    <p className="text-sm font-medium">{job.extraction.qualification.decision_maker || 'Неизвестен'}</p>
                                  </div>
                                </div>
                                
                                {job.extraction.qualification.need && (
                                  <div className="mt-4 bg-blue-50 p-4 rounded border border-blue-200">
                                    <p className="text-xs text-blue-700 font-medium mb-1">🎯 Потребность клиента</p>
                                    <p className="text-sm leading-relaxed">{job.extraction.qualification.need}</p>
                                  </div>
                                )}
                              </CardContent>
                            </Card>
                          </div>
                        )}

                        {/* Confidence */}
                        {job.extraction.confidence !== undefined && (
                          <div>
                            <h3 className="font-semibold mb-2">🎲 Confidence</h3>
                            <p className="text-2xl font-bold">{Math.round(job.extraction.confidence * 100)}%</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No extraction data available</p>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="transcript" className="mt-4">
                    {job?.transcript_segments && job.transcript_segments.length > 0 ? (
                      <div className="space-y-3">
                        {(() => {
                          // Get speaker roles from LLM extraction (if available)
                          const speakerRoles = job.extraction?.speaker_roles || {};
                          
                          // Fallback: assume first speaker is Sales Rep if LLM didn't identify
                          const firstSpeaker = job.transcript_segments.length > 0 
                            ? job.transcript_segments[0].speaker 
                            : null;
                          
                          // Helper function to get role
                          const getSpeakerRole = (speaker: string) => {
                            if (speakerRoles[speaker]) {
                              return speakerRoles[speaker];
                            }
                            // Fallback logic
                            return speaker === firstSpeaker ? 'Sales Rep' : 'Customer';
                          };
                          
                          return job.transcript_segments.map((segment: any, i: number) => {
                            const speakerLabel = segment.speaker || 'Unknown';
                            const speakerRole = getSpeakerRole(speakerLabel);
                            const isSalesRep = speakerRole === 'Sales Rep';
                            
                            // Count how many different speakers
                            const speakers = new Set(job.transcript_segments.map((s: any) => s.speaker));
                            const multiSpeaker = speakers.size > 1;
                            
                            return (
                              <div key={i} className={`border-l-4 rounded-lg p-4 ${
                                isSalesRep ? 'bg-blue-50 border-l-blue-500' : 'bg-gray-50 border-l-gray-400'
                              }`}>
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2">
                                    <Badge variant={isSalesRep ? 'default' : 'secondary'}>
                                      {multiSpeaker ? (
                                        isSalesRep ? '🎤 Sales Rep' : '👤 Customer'
                                      ) : (
                                        `🎤 ${speakerLabel}`
                                      )}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {Math.floor(segment.start / 60)}:{String(Math.floor(segment.start % 60)).padStart(2, '0')}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-sm leading-relaxed">{segment.text}</p>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    ) : job?.transcript ? (
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <pre className="whitespace-pre-wrap text-sm">{job.transcript}</pre>
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No transcript available</p>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="qa" className="mt-4">
                    {job?.transcript ? (
                      <div className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                          <div className="flex items-start gap-2">
                            <MessageCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                            <div>
                              <p className="font-semibold text-blue-900">Ask Questions About This Call</p>
                              <p className="text-sm text-blue-700">
                                Use AI to get specific answers based strictly on the transcript.
                                The AI will only use information from the call.
                              </p>
                            </div>
                          </div>
                        </div>
                        
                        {/* Q&A History */}
                        {qaHistory.length > 0 && (
                          <div className="space-y-3">
                            {qaHistory.map((qa, i) => (
                              <div key={i} className="space-y-2">
                                <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-500">
                                  <p className="font-semibold text-sm text-blue-900">❓ {qa.question}</p>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg border-l-4 border-gray-400">
                                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{qa.answer}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {/* Ask Question Form */}
                        <div className="flex gap-2">
                          <Input
                            placeholder="Ask a question about this call..."
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                handleAskQuestion()
                              }
                            }}
                            disabled={askingQuestion}
                            className="flex-1"
                          />
                          <Button
                            onClick={handleAskQuestion}
                            disabled={askingQuestion || !question.trim()}
                          >
                            {askingQuestion ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <>
                                <Send className="h-4 w-4 mr-2" />
                                Ask
                              </>
                            )}
                          </Button>
                        </div>
                        
                        {qaHistory.length === 0 && (
                          <div className="text-center py-8 text-muted-foreground">
                            <MessageCircle className="h-12 w-12 mx-auto mb-3 opacity-30" />
                            <p>No questions asked yet.</p>
                            <p className="text-sm">Try asking about specific moments, concerns, or next steps from the call.</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No transcript available for Q&A</p>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}


