from pydub import AudioSegment


def concat_wav_files(file_list, output_file="processed.wav", silence_duration=500):
    silence = AudioSegment.silent(duration=silence_duration)

    combined = AudioSegment.empty()
    for i, file in enumerate(file_list):
        audio = AudioSegment.from_file(file)
        combined += audio
        if i < len(file_list) - 1:
            combined += silence

    combined.export(output_file, format="wav")
    return output_file


def to_medical_format(anamnesis, client):
    user_query = "Please convert the following anamnesis into a structured but continuous clinical narrative, without headings or bullet points. Use correct terminology and concise paragraphs:\n\n"
    message = user_query + anamnesis
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a medical documentation assistant. Given informal or transcribed clinical notes, rewrite them into a formal medical narrative suitable for an EMR or referral letter. Use clear paragraph structure to enhance readability. Avoid using headings or bullet points. Employ precise and professional medical terminology in a continuous prose format."
            },
            {
                "role": "user",
                "content": message
            }
        ],
    )
    return response.choices[0].message.content 



