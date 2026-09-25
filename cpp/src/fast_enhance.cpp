#include "../include/fast_enhance.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

extern "C" {

void cpp_fast_contrast_threshold(
    const unsigned char* input_data,
    unsigned char* output_data,
    int width,
    int height,
    float clip_limit,
    int block_size
) {
    int total_pixels = width * height;
    if (total_pixels <= 0) return;

    unsigned char min_val = 255;
    unsigned char max_val = 0;
    for (int i = 0; i < total_pixels; ++i) {
        if (input_data[i] < min_val) min_val = input_data[i];
        if (input_data[i] > max_val) max_val = input_data[i];
    }

    float range = (max_val - min_val > 0) ? static_cast<float>(max_val - min_val) : 1.0f;
    int half_block = block_size / 2;

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int idx = y * width + x;
            
            float normalized = ((input_data[idx] - min_val) / range) * 255.0f;
            unsigned char contrast_pixel = static_cast<unsigned char>(std::clamp(normalized, 0.0f, 255.0f));

            int local_sum = 0;
            int count = 0;

            for (int dy = -half_block; dy <= half_block; dy += 2) {
                int ny = y + dy;
                if (ny >= 0 && ny < height) {
                    for (int dx = -half_block; dx <= half_block; dx += 2) {
                        int nx = x + dx;
                        if (nx >= 0 && nx < width) {
                            local_sum += input_data[ny * width + nx];
                            count++;
                        }
                    }
                }
            }

            int local_avg = (count > 0) ? (local_sum / count) : 128;
            output_data[idx] = (contrast_pixel > (local_avg - 10)) ? 255 : 0;
        }
    }
}

}