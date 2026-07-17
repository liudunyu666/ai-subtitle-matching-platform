import { useState } from 'react'
import {
  Typography, Upload, Input, Button, Card, message, Space, Alert,
} from 'antd'
import { InboxOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons'
import { createTask } from '../api'

const { Dragger } = Upload
const { TextArea } = Input

export default function NewTask({ onNavigate }) {
  const [fileList, setFileList] = useState([])
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('file')

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const formData = new FormData()
      if (mode === 'file') {
        if (fileList.length === 0) {
          message.warning('请上传文件')
          setLoading(false)
          return
        }
        formData.append('file', fileList[0].originFileObj || fileList[0])
        if (text.trim()) {
          formData.append('text', text.trim())
        }
      } else {
        if (!text.trim()) {
          message.warning('请输入字幕文本')
          setLoading(false)
          return
        }
        formData.append('text', text.trim())
      }
      const res = await createTask(formData)
      message.success('任务创建成功')
      onNavigate(`/task/${res.data.task_id}`)
    } catch (e) {
      message.error(e.message || '创建任务失败')
    } finally {
      setLoading(false)
    }
  }

  const uploadProps = {
    accept: '.mp4,.mov,.avi,.mp3,.wav,.m4a,.ogg',
    beforeUpload: (file) => {
      setFileList([file])
      return false
    },
    fileList,
    onRemove: () => setFileList([]),
    maxCount: 1,
  }

  const sampleText = `大家好，欢迎收看本期视频。今天我们来聊聊人工智能如何改变我们的生活。
从智能手机的语音助手到自动驾驶汽车，AI技术已经深入到各个领域。
在医疗领域，AI可以帮助医生更准确地诊断疾病。
在教育领域，AI可以根据每个学生的学习情况提供个性化的教学方案。
当然，AI的发展也带来了一些挑战。比如数据隐私和就业结构的变化。
但总的来说，AI为人类社会带来的机遇远大于挑战。
感谢大家的观看，我们下期再见。`

  return (
    <div className="page-container">
      <Typography.Title level={4}>新建任务</Typography.Title>

      <Card style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <Space>
            <Button
              type={mode === 'file' ? 'primary' : 'default'}
              icon={<InboxOutlined />}
              onClick={() => setMode('file')}
            >
              上传视频/音频
            </Button>
            <Button
              type={mode === 'text' ? 'primary' : 'default'}
              icon={<FileTextOutlined />}
              onClick={() => setMode('text')}
            >
              粘贴字幕文本
            </Button>
          </Space>
        </div>

        {mode === 'file' ? (
          <>
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">支持 MP4, MOV, AVI, MP3, WAV, M4A, OGG 格式</p>
            </Dragger>
            <Alert
              style={{ marginTop: 12 }}
              type="info"
              showIcon
              message="如无语音识别 API 密钥，可直接切换到「粘贴字幕文本」模式"
            />
            <div style={{ marginTop: 16 }}>
              <label style={{ display: 'block', marginBottom: 4, color: '#666' }}>字幕文本（可选，上传文件时同时提供文本将优先使用）</label>
              <TextArea
                rows={4}
                placeholder="可在此补充字幕文本..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>
          </>
        ) : (
          <>
            <TextArea
              rows={12}
              placeholder="请粘贴字幕文本..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div style={{ marginTop: 8 }}>
              <Button
                type="link"
                size="small"
                icon={<LinkOutlined />}
                onClick={() => setText(sampleText)}
              >
                填入示例文本
              </Button>
            </div>
          </>
        )}

        <Button
          type="primary"
          size="large"
          block
          style={{ marginTop: 16 }}
          loading={loading}
          onClick={handleSubmit}
        >
          {mode === 'file' ? '上传并创建任务' : '创建任务'}
        </Button>
      </Card>
    </div>
  )
}
