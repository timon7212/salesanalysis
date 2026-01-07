'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navigation } from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { formatDate, formatBytes } from '@/lib/utils'
import { ArrowLeft, Upload, FileAudio, Clock, CheckCircle2, XCircle, Loader2, ArrowRight } from 'lucide-react'

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const leadId = parseInt(params.id)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [lead, setLead] = useState<any>(null)
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  useEffect(() => {
    const apiKey = localStorage.getItem('apiKey')
    if (!apiKey) {
      router.push('/login')
      return
    }
    fetchLead()
    fetchJobs()
  }, [])

  const fetchLead = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await api.getLead(leadId)
      setLead(result)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch lead')
    } finally {
      setLoading(false)
    }
  }

  const fetchJobs = async () => {
    setLoadingJobs(true)
    try {
      const result = await api.getLeadJobs(leadId)
      // API now returns array directly, not {jobs: []}
      setJobs(Array.isArray(result) ? result : [])
    } catch (err: any) {
      console.error('Failed to fetch jobs:', err)
    } finally {
      setLoadingJobs(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    setUploadSuccess(false)

    try {
      const uploadResult = await api.uploadFile(file, leadId)
      
      // Create job
      const jobResult = await api.createJob(leadId, uploadResult.upload_id)
      
      setUploadSuccess(true)
      
      // Refresh jobs list
      fetchJobs()
      
      // Redirect to job page
      setTimeout(() => {
        router.push(`/jobs/${jobResult.job_id}`)
      }, 1000)
    } catch (err: any) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
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

  if (error && !lead) {
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
          <Link href="/leads">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Leads
            </Button>
          </Link>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>{lead?.lead_name || 'Lead Details'}</CardTitle>
              <CardDescription>Lead ID: {leadId}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Contact</p>
                  <p className="font-medium">{lead?.contact_name || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Price</p>
                  <p className="font-medium">{lead?.price ? `$${lead.price}` : '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="text-sm">{lead?.created_at ? formatDate(lead.created_at) : '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Updated</p>
                  <p className="text-sm">{lead?.updated_at ? formatDate(lead.updated_at) : '-'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Upload Call Recording</CardTitle>
              <CardDescription>
                Upload an audio or video file to analyze (MP3, WAV, M4A, MP4, MOV)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary transition-colors cursor-pointer"
                     onClick={() => fileInputRef.current?.click()}>
                  <FileAudio className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">
                    {uploading ? 'Uploading...' : 'Click to select file or drag and drop'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Max file size: 200MB
                  </p>
                </div>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".mp3,.wav,.m4a,.mp4,.mov"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={uploading}
                />

                {error && (
                  <div className="bg-destructive/10 text-destructive px-4 py-3 rounded">
                    {error}
                  </div>
                )}

                {uploadSuccess && (
                  <div className="bg-green-50 text-green-700 px-4 py-3 rounded">
                    Upload successful! Redirecting to job...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Job History */}
          <Card>
            <CardHeader>
              <CardTitle>Анализы звонков</CardTitle>
              <CardDescription>
                История всех обработок для этого лида
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingJobs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-muted-foreground">Загрузка...</span>
                </div>
              ) : jobs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileAudio className="h-12 w-12 mx-auto mb-2 opacity-30" />
                  <p>Анализы пока не созданы</p>
                  <p className="text-sm mt-1">Загрузите запись звонка выше</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {jobs.map((job) => (
                    <JobCard key={job.job_id} job={job} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />Завершено</Badge>
    case 'failed':
      return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Ошибка</Badge>
    case 'processing':
      return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Обработка</Badge>
    case 'queued':
      return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />В очереди</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

function JobCard({ job }: { job: any }) {
  const router = useRouter()
  const extraction = job.extraction

  return (
    <div 
      className="border rounded-lg p-4 hover:border-primary transition-colors cursor-pointer"
      onClick={() => router.push(`/jobs/${job.job_id}`)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <FileAudio className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">{job.filename}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            {formatDate(job.created_at)}
            {job.completed_at && ` • Завершено: ${formatDate(job.completed_at)}`}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge(job.status)}
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>

      {extraction && job.status === 'completed' && (
        <div className="mt-3 pt-3 border-t space-y-2">
          {/* Qualification Score */}
          {extraction.qualification?.score !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Оценка:</span>
              <Badge 
                className={
                  extraction.qualification.score >= 76 ? 'bg-green-500' :
                  extraction.qualification.score >= 56 ? 'bg-orange-500' :
                  extraction.qualification.score >= 31 ? 'bg-yellow-500' :
                  'bg-gray-500'
                }
              >
                {extraction.qualification.score}/100
              </Badge>
              <span className="text-xs text-muted-foreground">
                {extraction.qualification.score >= 76 ? '🔥 Горячий' :
                 extraction.qualification.score >= 56 ? '⚡ Теплый' :
                 extraction.qualification.score >= 31 ? '❄️ Холодный' :
                 '🧊 Ранний'}
              </span>
            </div>
          )}

          {/* Top Concerns */}
          {extraction.concerns && extraction.concerns.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Проблемы:</span>
              <div className="flex flex-wrap gap-1">
                {extraction.concerns.slice(0, 3).map((concern: any, idx: number) => (
                  <Badge 
                    key={idx} 
                    variant="outline"
                    className={
                      concern.severity >= 4 ? 'border-red-500 text-red-700' :
                      concern.severity >= 3 ? 'border-orange-500 text-orange-700' :
                      'border-gray-300'
                    }
                  >
                    {concern.type} ({concern.severity}/5)
                  </Badge>
                ))}
                {extraction.concerns.length > 3 && (
                  <Badge variant="outline">+{extraction.concerns.length - 3}</Badge>
                )}
              </div>
            </div>
          )}

          {/* Next Steps Count */}
          {extraction.next_steps && extraction.next_steps.length > 0 && (
            <div className="text-xs text-muted-foreground">
              📋 Следующих шагов: {extraction.next_steps.length}
            </div>
          )}
        </div>
      )}

      {job.status === 'failed' && job.error_message && (
        <div className="mt-3 pt-3 border-t">
          <p className="text-xs text-destructive">{job.error_message}</p>
        </div>
      )}
    </div>
  )
}


