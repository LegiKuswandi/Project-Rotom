#ifndef FAST_ENHANCE_HPP
#define FAST_ENHANCE_HPP

#ifdef __cplusplus
extern "C" {
#endif

void cpp_fast_contrast_threshold(
    const unsigned char* input_data,
    unsigned char* output_data,
    int width,
    int height,
    float clip_limit,
    int block_size
);

#ifdef __cplusplus
}
#endif

#endif // FAST_ENHANCE_HPP