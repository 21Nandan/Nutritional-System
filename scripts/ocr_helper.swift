import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("{\"error\": \"Missing image path argument\"}")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let fileURL = URL(fileURLWithPath: imagePath)

guard let image = NSImage(contentsOf: fileURL),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("{\"error\": \"Failed to load image at \(imagePath)\"}")
    exit(1)
}

let request = VNRecognizeTextRequest { (request, error) in
    if let error = error {
        print("{\"error\": \"\(error.localizedDescription)\"}")
        return
    }

    guard let observations = request.results as? [VNRecognizedTextObservation] else {
        print("{\"lines\": []}")
        return
    }

    var lines: [String] = []
    for observation in observations {
        if let topCandidate = observation.topCandidates(1).first {
            lines.append(topCandidate.string)
        }
    }

    let fullText = lines.joined(separator: "\n")
    let jsonOutput: [String: Any] = [
        "status": "success",
        "full_text": fullText,
        "lines": lines
    ]

    if let jsonData = try? JSONSerialization.data(withJSONObject: jsonOutput, options: .prettyPrinted),
       let jsonString = String(data: jsonData, encoding: .utf8) {
        print(jsonString)
    }
}

request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    print("{\"error\": \"Failed to perform text recognition: \(error.localizedDescription)\"}")
}
