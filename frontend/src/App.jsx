import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ChatInterface from './components/ChatInterface'

export default function App() {
  const [docInfo, setDocInfo]       = useState(null)   // null = upload screen
  const [isUploading, setIsUploading] = useState(false)

  const handleUploadSuccess = (data) => {
    setDocInfo(data)
  }

  const handleReset = () => {
    setDocInfo(null)
  }

  return (
    <div className="h-full">
      {docInfo ? (
        <ChatInterface
          docInfo={docInfo}
          onReset={handleReset}
        />
      ) : (
        <FileUpload
          onUploadSuccess={handleUploadSuccess}
          isUploading={isUploading}
          setIsUploading={setIsUploading}
        />
      )}
    </div>
  )
}
