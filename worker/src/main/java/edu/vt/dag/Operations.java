package edu.vt.dag;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import static edu.vt.dag.Model.*;

/** Fixed allowlist: manifests cannot supply shell commands, code, paths, or codec arguments. */
public final class Operations {
    public record Product(Path file,String mediaType) {}
    private final ArtifactClient artifacts;
    public Operations(ArtifactClient artifacts){this.artifacts=artifacts;}
    public Map<String,Product> execute(Assignment a,Path dir) throws Exception {
        var files=new TreeMap<String,Path>();
        for(var e:a.inputs().entrySet())files.put(e.getKey(),artifacts.get(e.getValue(),dir.resolve("input-"+e.getKey())));
        var t=a.task();var p=t.parameters();String operation=t.operation();
        if(operation.startsWith("fixture_"))Thread.sleep(p.delay_ms()==null?100:p.delay_ms());
        var outputs=new TreeMap<String,Product>();
        Path output=dir.resolve("output");
        switch(operation) {
            case "fixture_write" -> value(outputs,output,p.value());
            case "fixture_add" -> value(outputs,output,Math.addExact(integer(files.get("value")),p.amount()));
            case "fixture_multiply" -> value(outputs,output,Math.multiplyExact(integer(files.get("value")),p.amount()));
            case "fixture_sum" -> {long sum=0;for(Path file:files.values())sum=Math.addExact(sum,integer(file));value(outputs,output,sum);}
            case "fixture_format" -> {Files.writeString(output,"result="+integer(files.get("value"))+"\n");outputs.put("text",new Product(output,"text/plain"));}
            case "video_inspect" -> {probe(files.get("video"),output,dir);outputs.put("metadata",new Product(output,"application/json"));}
            case "video_transcode" -> {
                output=dir.resolve("output.mp4");
                command(List.of("ffmpeg","-nostdin","-v","error","-y","-threads","1","-i",files.get("video").toString(),"-vf","scale=-2:"+p.height(),"-filter_threads","1","-c:v","libx264","-preset","veryfast","-crf","28","-threads","1","-an","-movflags","+faststart",output.toString()),dir,null);
                outputs.put("video",new Product(output,"video/mp4"));
            }
            case "video_thumbnail" -> {
                output=dir.resolve("output.png");
                command(List.of("ffmpeg","-nostdin","-v","error","-y","-threads","1","-i",files.get("video").toString(),"-frames:v","1","-threads","1",output.toString()),dir,null);
                outputs.put("image",new Product(output,"image/png"));
            }
            case "fixture_subtitles" -> {Files.copy(files.get("srt"),output);outputs.put("subtitles",new Product(output,"application/x-subrip"));}
            case "video_publish" -> {
                var metadata=new TreeMap<String,Object>();
                for(String name:List.of("video720","video360")) {
                    Path info=dir.resolve(name+".json");probe(files.get(name),info,dir);metadata.put(name,Json.MAPPER.readTree(Files.readAllBytes(info)));
                }
                Files.write(output,Json.bytes(Map.of("schema_version",1,"fixture_subtitles",true,"artifacts",a.inputs(),"metadata",metadata)));
                outputs.put("manifest",new Product(output,"application/json"));
            }
            default -> throw new IOException("Unsupported operation");
        }
        for(var product:outputs.values())if(!Files.isRegularFile(product.file()) || Files.size(product.file())>ManifestValidator.MAX_ARTIFACT)throw new IOException("Invalid operation output");
        return outputs;
    }
    private static long integer(Path p)throws IOException {return Json.read(Files.readAllBytes(p),Long.class);}
    private static void value(Map<String,Product> outputs,Path path,long n)throws IOException {Files.write(path,Json.bytes(n));outputs.put("value",new Product(path,"application/json"));}
    private static void probe(Path input,Path output,Path dir)throws Exception {
        command(List.of("ffprobe","-v","error","-show_streams","-show_format","-of","json",input.toString()),dir,output);
        var info=Json.MAPPER.readTree(Files.readAllBytes(output));if(!info.has("streams")||info.get("streams").isEmpty())throw new IOException("Unreadable video");
    }
    private static void command(List<String> command,Path dir,Path stdout)throws Exception {
        var builder=new ProcessBuilder(command).redirectError(dir.resolve("media-error.log").toFile());
        builder.redirectOutput(stdout==null?ProcessBuilder.Redirect.DISCARD:ProcessBuilder.Redirect.to(stdout.toFile()));
        var process=builder.start();
        try{if(process.waitFor()!=0)throw new IOException("Media operation failed: "+Files.readString(dir.resolve("media-error.log")).substring(0,(int)Math.min(1024,Files.size(dir.resolve("media-error.log")))));}
        finally{if(process.isAlive()){process.destroyForcibly();process.waitFor();}}
    }
}
