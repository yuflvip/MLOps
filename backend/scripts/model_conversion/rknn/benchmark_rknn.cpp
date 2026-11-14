// Board-only benchmark: one image preprocessing, exactly 200 synchronous runs,
// one output retrieval and one YOLOv8 nine-output postprocessing.
// Build with RKNN Runtime headers + stb_image.h; link -lrknnrt -lm.
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#include "rknn_api.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <time.h>
#include <vector>

static double now_ms() {
    timespec ts{};
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}
static void check(int code, const char* operation) {
    if (code < 0) throw std::runtime_error(std::string(operation) + ": " + std::to_string(code));
}
struct Box { float x1, y1, x2, y2, score; int cls; };
static float iou(const Box& a, const Box& b) {
    float overlap = std::max(0.f, std::min(a.x2,b.x2)-std::max(a.x1,b.x1)) *
                    std::max(0.f, std::min(a.y2,b.y2)-std::max(a.y1,b.y1));
    return overlap / std::max(1e-9f, (a.x2-a.x1)*(a.y2-a.y1)+(b.x2-b.x1)*(b.y2-b.y1)-overlap);
}

struct Image {
    int width, height, left, top;
    double scale;
    std::vector<unsigned char> rgb;
};
static Image preprocess(const char* path) {
    Image out{};
    int channels;
    unsigned char* data = stbi_load(path, &out.width, &out.height, &channels, 3);
    if (!data) throw std::runtime_error("Cannot decode input image");
    out.scale = std::min(640.0/out.width, 640.0/out.height);
    int w = std::max(1, (int)std::nearbyint(out.width*out.scale));
    int h = std::max(1, (int)std::nearbyint(out.height*out.scale));
    out.left = (640-w)/2; out.top = (640-h)/2;
    out.rgb.assign(640*640*3, 114);
    // Half-pixel bilinear resize, RGB, centered letterbox with padding 114.
    for (int y=0; y<h; ++y) {
        double sy = (y+.5)*out.height/h-.5;
        int iy=(int)std::floor(sy), y0=std::max(0,iy), y1=std::min(out.height-1,iy+1);
        double fy=sy-iy;
        for (int x=0; x<w; ++x) {
            double sx=(x+.5)*out.width/w-.5;
            int ix=(int)std::floor(sx), x0=std::max(0,ix), x1=std::min(out.width-1,ix+1);
            double fx=sx-ix;
            for (int c=0; c<3; ++c) {
                double a=data[(y0*out.width+x0)*3+c]*(1-fx)+data[(y0*out.width+x1)*3+c]*fx;
                double b=data[(y1*out.width+x0)*3+c]*(1-fx)+data[(y1*out.width+x1)*3+c]*fx;
                out.rgb[((y+out.top)*640+x+out.left)*3+c]=(unsigned char)std::lround(a*(1-fy)+b*fy);
            }
        }
    }
    stbi_image_free(data);
    return out;
}
static std::vector<Box> postprocess(const std::vector<rknn_output>& outputs,
                                    const std::vector<rknn_tensor_attr>& attrs, const Image& img) {
    std::vector<Box> candidates;
    for (int scale=0; scale<3; ++scale) {
        int stride=8<<scale, h=640/stride, w=h, count=h*w;
        int bins=attrs[scale*3].dims[1]/4, classes=attrs[scale*3+1].dims[1];
        const float* boxes=(const float*)outputs[scale*3].buf;
        const float* scores=(const float*)outputs[scale*3+1].buf;
        for (int p=0; p<count; ++p) {
            int cls=0; float score=scores[p];
            for (int c=1; c<classes; ++c) if (scores[c*count+p]>score) {cls=c;score=scores[c*count+p];}
            if (!std::isfinite(score)) throw std::runtime_error("Nonfinite output");
            if (score<=.25f) continue;
            float dist[4];
            for (int side=0; side<4; ++side) {
                float maximum=-INFINITY;
                for (int k=0;k<bins;++k) maximum=std::max(maximum,boxes[(side*bins+k)*count+p]);
                float total=0, weighted=0;
                for (int k=0;k<bins;++k) {float q=std::exp(boxes[(side*bins+k)*count+p]-maximum); total+=q;weighted+=q*k;}
                dist[side]=weighted/total;
                if (!std::isfinite(dist[side])) throw std::runtime_error("Nonfinite DFL output");
            }
            float cx=p%w+.5f, cy=p/w+.5f;
            candidates.push_back({(cx-dist[0])*stride,(cy-dist[1])*stride,
                                  (cx+dist[2])*stride,(cy+dist[3])*stride,score,cls});
        }
    }
    std::stable_sort(candidates.begin(),candidates.end(),[](const Box& a,const Box& b){return a.score>b.score;});
    std::vector<Box> selected;
    for (const auto& box:candidates) {
        bool suppressed=false;
        for (const auto& prev:selected) if (prev.cls==box.cls && iou(prev,box)>.45f) {suppressed=true;break;}
        if (!suppressed) selected.push_back(box);
    }
    for (auto& box:selected) {
        box.x1=std::clamp((float)((box.x1-img.left)/img.scale),0.f,(float)img.width);
        box.x2=std::clamp((float)((box.x2-img.left)/img.scale),0.f,(float)img.width);
        box.y1=std::clamp((float)((box.y1-img.top)/img.scale),0.f,(float)img.height);
        box.y2=std::clamp((float)((box.y2-img.top)/img.scale),0.f,(float)img.height);
    }
    return selected;
}

int main(int argc,char** argv) {
    if(argc!=4) {std::fprintf(stderr,"usage: benchmark model.rknn input.jpg fp16|int8|hybrid\n");return 2;}
    std::string label=argv[3];
    if(label!="fp16" && label!="int8" && label!="hybrid") return 2;
    rknn_context ctx=0; bool acquired=false;
    std::vector<rknn_output> outputs(9);
    try {
        double start=now_ms();check(rknn_init(&ctx,argv[1],0,0,nullptr),"init");
        check(rknn_set_core_mask(ctx,RKNN_NPU_CORE_0_1_2),"set_core_mask");
        double load_ms=now_ms()-start;
        rknn_sdk_version version{};check(rknn_query(ctx,RKNN_QUERY_SDK_VERSION,&version,sizeof(version)),"version");
        rknn_input_output_num io{};check(rknn_query(ctx,RKNN_QUERY_IN_OUT_NUM,&io,sizeof(io)),"io count");
        if(io.n_input!=1 || io.n_output!=9) throw std::runtime_error("Requires nine-output YOLOv8 model");
        rknn_tensor_attr input{};check(rknn_query(ctx,RKNN_QUERY_INPUT_ATTR,&input,sizeof(input)),"input");
        if(input.n_elems!=640*640*3) throw std::runtime_error("Requires 640x640 RGB model");
        std::vector<rknn_tensor_attr> attrs(9);
        for(int i=0;i<9;++i) {
            attrs[i].index=i;check(rknn_query(ctx,RKNN_QUERY_OUTPUT_ATTR,&attrs[i],sizeof(attrs[i])),"output");
            int h=80>>(i/3);
            if(attrs[i].n_dims!=4 || attrs[i].dims[0]!=1 || attrs[i].dims[2]!=h || attrs[i].dims[3]!=h ||
               (i%3==0 && attrs[i].dims[1]!=64) || (i%3==2 && attrs[i].dims[1]!=1))
                throw std::runtime_error("Unexpected output layout");
            outputs[i].index=i;outputs[i].want_float=1;
        }
        start=now_ms();Image image=preprocess(argv[2]);double prep_ms=now_ms()-start;
        rknn_input in{};in.buf=image.rgb.data();in.size=image.rgb.size();in.type=RKNN_TENSOR_UINT8;in.fmt=RKNN_TENSOR_NHWC;
        start=now_ms();check(rknn_inputs_set(ctx,1,&in),"inputs_set");double input_ms=now_ms()-start;
        std::vector<double> timings;timings.reserve(200);
        double loop_start=now_ms();
        // flags=0 at init: synchronous/blocking calls; no additional warm-up runs.
        for(int i=0;i<200;++i) {start=now_ms();check(rknn_run(ctx,nullptr),"run");timings.push_back(now_ms()-start);}
        double loop_ms=now_ms()-loop_start;
        start=now_ms();check(rknn_outputs_get(ctx,9,outputs.data(),nullptr),"outputs_get");acquired=true;
        double get_ms=now_ms()-start;
        start=now_ms();auto detections=postprocess(outputs,attrs,image);double post_ms=now_ms()-start;
        auto sorted=timings;std::sort(sorted.begin(),sorted.end());double sum=0;for(double t:timings)sum+=t;
        std::printf("Runtime=%s Driver=%s\n",version.api_version,version.drv_version);
        std::printf("BENCH_JSON {\"precision\":\"%s\",\"runs\":200,\"preprocess_calls\":1,\"input_set_calls\":1,\"output_get_calls\":1,\"postprocess_calls\":1,\"warmup_runs\":0,\"npu_core_mask\":7,\"load_ms\":%.6f,\"preprocess_ms\":%.6f,\"input_set_ms\":%.6f,\"inference_sum_ms\":%.6f,\"loop_wall_ms\":%.6f,\"mean_ms\":%.6f,\"p50_ms\":%.6f,\"p95_ms\":%.6f,\"min_ms\":%.6f,\"max_ms\":%.6f,\"first_ms\":%.6f,\"inference_fps\":%.6f,\"output_get_ms\":%.6f,\"postprocess_cpu_ms\":%.6f,\"detections\":%zu,\"timings_ms\":[",
                    label.c_str(),load_ms,prep_ms,input_ms,sum,loop_ms,sum/200,(sorted[99]+sorted[100])/2,sorted[189],sorted[0],sorted[199],timings[0],200000/sum,get_ms,post_ms,detections.size());
        for(size_t i=0;i<timings.size();++i) std::printf("%s%.6f",i?",":"",timings[i]);std::puts("]}");
        check(rknn_outputs_release(ctx,9,outputs.data()),"release");acquired=false;check(rknn_destroy(ctx),"destroy");ctx=0;
        return 0;
    } catch(const std::exception& error) {
        std::fprintf(stderr,"%s\n",error.what());
        if(acquired) rknn_outputs_release(ctx,9,outputs.data());if(ctx)rknn_destroy(ctx);return 1;
    }
}
